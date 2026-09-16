import argparse
import json
import os
import re
import select
import signal
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logio import RotatingLogWriter, finalize_active_log
from storage import (
    OmaRunError,
    PYTHON_EXECUTABLE,
    SYSTEMCTL_EXECUTABLE,
    control_environment,
    get_task,
    load_tasks,
    task_state_dir,
    verify_trusted_executable,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_status(state_dir: Path, payload: dict[str, Any]) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=state_dir, prefix=".tmp-status-", text=True)
    try:
        with open(fd, "w", encoding="utf-8") as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
        Path(tmp_path).replace(state_dir / "status.json")
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink(missing_ok=True)


def _build_argv(task: dict[str, Any]) -> list[str]:
    command = str(task.get("command", "")).strip()
    if not command:
        raise OmaRunError("Command is required.")

    arguments = str(task.get("arguments", "")).strip()
    argv = shlex.split(command)
    if arguments:
        argv.extend(shlex.split(arguments))
    return argv


def _manager_environment() -> dict[str, str]:
    """Read ordinary manager variables only after trusted Python startup."""
    try:
        verify_trusted_executable(SYSTEMCTL_EXECUTABLE)
        result = subprocess.run(
            [
                str(SYSTEMCTL_EXECUTABLE),
                "--user",
                "show-environment",
            ],
            check=False,
            text=True,
            capture_output=True,
            env=control_environment(),
        )
    except OSError:
        return {}
    if result.returncode != 0:
        return {}
    environment: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if (
            separator
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
            and not value.startswith("$'")
        ):
            environment[name] = value
    return environment


def _build_env(task: dict[str, Any]) -> dict[str, str]:
    env = control_environment()
    env.update(_manager_environment())
    extra_env = task.get("env", {}) or {}
    if not isinstance(extra_env, dict):
        raise OmaRunError("env must be a key/value object.")
    for key, value in extra_env.items():
        env[str(key)] = str(value)
    return env


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    """Stop the command and any children it created."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def run_task(task_id: str) -> int:
    tasks = load_tasks()
    task = get_task(tasks, task_id)
    state_dir = task_state_dir(task_id)
    started_at = _utc_now()
    start_ts = time.monotonic()
    raw_command = str(task.get("command", "")).strip()
    raw_arguments = str(task.get("arguments", "")).strip()
    displayed_command = " ".join(part for part in (raw_command, raw_arguments) if part)
    launch_error: Exception | None = None

    output = RotatingLogWriter(state_dir)
    try:
        output.write(f"$ {displayed_command}\n\n".encode("utf-8", errors="replace"))
        try:
            argv = _build_argv(task)
            env = _build_env(task)
            working_directory = str(task.get("workingDirectory", "")).strip()
            timeout_seconds = int(task.get("timeoutSeconds", 0) or 0)

            if working_directory and not Path(working_directory).exists():
                raise OmaRunError(f"Working directory does not exist: {working_directory}")

            process = subprocess.Popen(
                argv,
                cwd=working_directory or None,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                bufsize=0,
            )
        except Exception as exc:
            launch_error = exc
            output.write(f"[ERROR] {exc}\n".encode("utf-8", errors="replace"))

        if launch_error is not None:
            process = None

        timed_out = False
        stopped_by_user = False
        stop_requested = False

        def request_stop(_signum: int, _frame: Any) -> None:
            nonlocal stop_requested
            stop_requested = True

        if process is not None:
            assert process.stdout is not None
            output_fd = process.stdout.fileno()
            previous_sigterm = signal.signal(signal.SIGTERM, request_stop)
            termination_deadline: float | None = None
            main_exit_seen_at: float | None = None
            try:
                deadline = time.monotonic() + timeout_seconds if timeout_seconds > 0 else None
                pipe_open = True
                while pipe_open or process.poll() is None:
                    now = time.monotonic()
                    if stop_requested and process.poll() is None and termination_deadline is None:
                        stopped_by_user = True
                        _terminate_process_group(process)
                        termination_deadline = now + 10
                    if (
                        deadline is not None
                        and now >= deadline
                        and process.poll() is None
                        and termination_deadline is None
                    ):
                        timed_out = True
                        _terminate_process_group(process)
                        termination_deadline = now + 10
                    if (
                        termination_deadline is not None
                        and now >= termination_deadline
                        and process.poll() is None
                    ):
                        _kill_process_group(process)
                        termination_deadline = None

                    if pipe_open:
                        readable, _writable, _errors = select.select([output_fd], [], [], 0.1)
                        if readable:
                            chunk = os.read(output_fd, 65536)
                            if chunk:
                                output.write(chunk)
                            else:
                                pipe_open = False
                    else:
                        time.sleep(0.05)

                    if process.poll() is not None:
                        if main_exit_seen_at is None:
                            main_exit_seen_at = now
                        elif pipe_open and now - main_exit_seen_at >= 1:
                            # A detached descendant may retain stdout forever.
                            pipe_open = False
            except KeyboardInterrupt:
                stopped_by_user = True
                _terminate_process_group(process)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    _kill_process_group(process)
                    process.wait(timeout=10)
            finally:
                signal.signal(signal.SIGTERM, previous_sigterm)
                process.stdout.close()
                if process.poll() is None:
                    process.wait(timeout=10)
        output.close()
        finalize_active_log(state_dir)
    finally:
        output.close()

    duration_ms = int((time.monotonic() - start_ts) * 1000)
    if launch_error is not None:
        message = f"Failed to start: {launch_error}"
        _write_status(
            state_dir,
            {
                "status": "failed",
                "message": message,
                "exitCode": 2,
                "startedAt": started_at,
                "finishedAt": _utc_now(),
                "durationMs": duration_ms,
            },
        )
        raise launch_error

    assert process is not None
    exit_code = process.returncode if process.returncode is not None else 1
    finished_at = _utc_now()

    if timed_out:
        status = "timed_out"
        message = f"Timed out after {timeout_seconds} seconds"
    elif stopped_by_user:
        status = "stopped"
        message = "Stopped by user"
    elif exit_code == 0:
        status = "success"
        message = "Completed successfully"
    else:
        status = "failed"
        message = f"Exit code {exit_code}"

    _write_status(
        state_dir,
        {
            "status": status,
            "message": message,
            "exitCode": exit_code,
            "startedAt": started_at,
            "finishedAt": finished_at,
            "durationMs": duration_ms,
        },
    )
    # A user-initiated stop is an expected service shutdown, not a failed run.
    return 0 if stopped_by_user else exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OmaRun task runner")
    parser.add_argument("--task-id", required=True, help="Immutable task identifier")
    return parser.parse_args()


def _verify_python_runtime() -> None:
    expected = verify_trusted_executable(PYTHON_EXECUTABLE)
    try:
        current = Path(sys.executable).resolve(strict=True)
    except OSError as exc:
        raise OmaRunError("Unable to verify the running Python interpreter.") from exc
    if current != expected:
        raise OmaRunError(f"OmaRun must use the trusted interpreter at {PYTHON_EXECUTABLE}.")


def main() -> int:
    _verify_python_runtime()
    args = parse_args()
    try:
        return run_task(args.task_id)
    except FileNotFoundError as exc:
        raise OmaRunError(f"Executable not found: {exc.filename}") from exc


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OmaRunError as exc:
        print(f"error: {exc}")
        raise SystemExit(2)
