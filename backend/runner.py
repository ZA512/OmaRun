import argparse
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage import OmaRunError, get_task, load_tasks, task_state_dir


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


def _build_env(task: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    extra_env = task.get("env", {}) or {}
    if not isinstance(extra_env, dict):
        raise OmaRunError("env must be a key/value object.")
    for key, value in extra_env.items():
        env[str(key)] = str(value)
    return env


def _copy_current_to_last(state_dir: Path) -> None:
    current_log = state_dir / "current.log"
    if not current_log.exists():
        return
    fd, tmp_path = tempfile.mkstemp(dir=state_dir, prefix=".tmp-last-")
    try:
        with open(fd, "wb") as tmp:
            with current_log.open("rb") as source:
                shutil.copyfileobj(source, tmp)
        Path(tmp_path).replace(state_dir / "last.log")
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink(missing_ok=True)


def run_task(task_id: str) -> int:
    tasks = load_tasks()
    task = get_task(tasks, task_id)
    state_dir = task_state_dir(task_id)
    started_at = _utc_now()
    start_ts = time.monotonic()

    argv = _build_argv(task)
    env = _build_env(task)
    working_directory = str(task.get("workingDirectory", "")).strip()
    timeout_seconds = int(task.get("timeoutSeconds", 0) or 0)

    if working_directory and not Path(working_directory).exists():
        raise OmaRunError(f"Working directory does not exist: {working_directory}")

    current_log = state_dir / "current.log"
    with current_log.open("w", encoding="utf-8", buffering=1) as output:
        output.write(f"$ {' '.join(shlex.quote(arg) for arg in argv)}\n\n")
        process = subprocess.Popen(
            argv,
            cwd=working_directory or None,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        timed_out = False
        stopped_by_user = False
        try:
            process.wait(timeout=timeout_seconds if timeout_seconds > 0 else None)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        except KeyboardInterrupt:
            stopped_by_user = True
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)

    duration_ms = int((time.monotonic() - start_ts) * 1000)
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

    _copy_current_to_last(state_dir)
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
    return exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OmaRun task runner")
    parser.add_argument("--task-id", required=True, help="Immutable task identifier")
    return parser.parse_args()


def main() -> int:
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
