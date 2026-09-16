import argparse
import copy
import ctypes
import errno
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import secrets
from pathlib import Path
from typing import Any

from logio import RESPONSE_MARKER, read_active_log, read_file_tail
from storage import (
    ENV_EXECUTABLE,
    LOG_RESPONSE_BYTES,
    LOG_STORAGE_BYTES,
    OmaRunError,
    PYTHON_EXECUTABLE,
    SYSTEMCTL_EXECUTABLE,
    SYSTEMD_USER_DIR,
    control_environment,
    get_task,
    load_tasks,
    make_task_id,
    save_tasks,
    task_state_dir,
    validate_task_id,
    verify_trusted_executable,
)


UNIT_READ_LIMIT = 64 * 1024
UNIT_MARKER_PRODUCT = "io.github.za512.omarun"
RENAME_NOREPLACE = 1
RENAME_EXCHANGE = 2


def _service_name(task_id: str) -> str:
    return f"omarun-{task_id}.service"


def _timer_name(task_id: str) -> str:
    return f"omarun-{task_id}.timer"


def _run_systemctl(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    verify_trusted_executable(SYSTEMCTL_EXECUTABLE)
    cmd = [str(SYSTEMCTL_EXECUTABLE), "--user", *args]
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=True,
        env=control_environment(),
    )


def _daemon_reload() -> None:
    _run_systemctl(["daemon-reload"])


def _normalize_schedule(schedule: dict[str, Any] | None) -> dict[str, Any]:
    if not schedule:
        return {"enabled": False}
    enabled = bool(schedule.get("enabled", False))
    mode = str(schedule.get("mode", "")).strip()
    interval = int(schedule.get("interval", 0) or 0)
    at_time = str(schedule.get("time", "03:00")).strip()
    weekdays = schedule.get("weekdays", []) or []
    if enabled and mode not in {
        "every-minutes",
        "every-hours",
        "every-days",
        "daily-at",
        "weekly",
    }:
        raise OmaRunError("Invalid schedule mode.")
    if mode in {"every-minutes", "every-hours", "every-days"} and interval <= 0:
        raise OmaRunError("Interval must be greater than 0.")
    if mode in {"daily-at", "weekly"}:
        try:
            time_parts = at_time.split(":")
            if len(time_parts) != 2 or any(len(part) != 2 for part in time_parts):
                raise ValueError
            hour, minute = (int(part) for part in time_parts)
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError
        except ValueError as exc:
            raise OmaRunError("Time must use HH:MM.") from exc
    return {
        "enabled": enabled,
        "mode": mode,
        "interval": interval,
        "time": at_time,
        "weekdays": weekdays,
    }


def _schedule_to_timer_lines(schedule: dict[str, Any]) -> list[str]:
    mode = schedule["mode"]
    if mode == "every-minutes":
        interval = f"{schedule['interval']}min"
        return [f"OnActiveSec={interval}", f"OnUnitActiveSec={interval}"]
    if mode == "every-hours":
        interval = f"{schedule['interval']}h"
        return [f"OnActiveSec={interval}", f"OnUnitActiveSec={interval}"]
    if mode == "every-days":
        interval = f"{schedule['interval']}d"
        return [f"OnActiveSec={interval}", f"OnUnitActiveSec={interval}"]
    if mode == "daily-at":
        return [f"OnCalendar=*-*-* {schedule['time']}:00"]
    if mode == "weekly":
        weekdays_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        selected = schedule.get("weekdays", []) or []
        if not selected:
            raise OmaRunError("Weekly mode requires at least one weekday.")
        parsed_days = []
        for value in selected:
            day_index = int(value)
            if day_index < 0 or day_index > 6:
                raise OmaRunError("Weekdays must be integers from 0 (Mon) to 6 (Sun).")
            parsed_days.append(weekdays_map[day_index])
        values = ",".join(parsed_days)
        return [f"OnCalendar={values} *-*-* {schedule['time']}:00"]
    raise OmaRunError("Unsupported schedule mode.")


def _safe_description(value: Any) -> str:
    return "".join(
        " " if ord(character) < 32 or ord(character) == 127 else character
        for character in str(value)
    ).strip()


def _systemd_quote(value: str) -> str:
    return shlex.quote(value.replace("%", "%%"))


def _unit_marker(task_id: str, kind: str) -> str:
    validate_task_id(task_id)
    if kind not in {"service", "timer"}:
        raise OmaRunError(f"Invalid OmaRun unit kind: {kind}")
    return f"# Managed-By={UNIT_MARKER_PRODUCT} Task={task_id} Kind={kind}"


def _service_content(task: dict[str, Any]) -> str:
    task_id = task["id"]
    validate_task_id(task_id)
    runner_path = Path(__file__).resolve().parent / "runner.py"
    verify_trusted_executable(PYTHON_EXECUTABLE)
    verify_trusted_executable(ENV_EXECUTABLE)
    exec_start = " ".join(
        [
            str(ENV_EXECUTABLE),
            "-i",
            "HOME=%h",
            "USER=%u",
            "LOGNAME=%u",
            "SHELL=/bin/sh",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "LANG=C.UTF-8",
            "LC_ALL=C.UTF-8",
            "XDG_RUNTIME_DIR=%t",
            "DBUS_SESSION_BUS_ADDRESS=unix:path=%t/bus",
            str(PYTHON_EXECUTABLE),
            "-E",
            "-s",
            "-X",
            "utf8",
            _systemd_quote(str(runner_path)),
            "--task-id",
            _systemd_quote(task_id),
        ]
    )
    description = _safe_description(task["name"])
    lines = [
        _unit_marker(task_id, "service"),
        "[Unit]",
        f"Description=OmaRun task {description}",
        "",
        "[Service]",
        "Type=simple",
        "KillMode=process",
        "TimeoutStopSec=15",
        f"ExecStart={exec_start}",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ]
    return "\n".join(lines)


def _legacy_service_content(task: dict[str, Any]) -> str:
    """Reconstruct the pre-hardening unit exactly; this is never written."""
    task_id = task["id"]
    validate_task_id(task_id)
    runner_path = Path(__file__).resolve().parent / "runner.py"
    return "\n".join(
        [
            "[Unit]",
            f"Description=OmaRun task {task['name']}",
            "",
            "[Service]",
            "Type=simple",
            "KillMode=process",
            "TimeoutStopSec=15",
            f"ExecStart=/usr/bin/env python3 {shlex.quote(str(runner_path))} --task-id {shlex.quote(task_id)}",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )


def _timer_content(task: dict[str, Any]) -> str:
    task_id = task["id"]
    validate_task_id(task_id)
    schedule = _normalize_schedule(task.get("schedule"))
    if not schedule["enabled"]:
        raise OmaRunError("Cannot render a disabled OmaRun timer.")
    lines = _schedule_to_timer_lines(schedule)
    description = _safe_description(task["name"])
    return "\n".join(
        [
            _unit_marker(task_id, "timer"),
            "[Unit]",
            f"Description=OmaRun schedule for {description}",
            "",
            "[Timer]",
            f"Unit={_service_name(task_id)}",
            *lines,
            "Persistent=true",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )


def _legacy_timer_content(task: dict[str, Any]) -> str:
    """Reconstruct the pre-hardening timer exactly; this is never written."""
    task_id = task["id"]
    validate_task_id(task_id)
    schedule = _normalize_schedule(task.get("schedule"))
    if not schedule["enabled"]:
        raise OmaRunError("Cannot render a disabled legacy OmaRun timer.")
    return "\n".join(
        [
            "[Unit]",
            f"Description=OmaRun schedule for {task['name']}",
            "",
            "[Timer]",
            f"Unit={_service_name(task_id)}",
            *_schedule_to_timer_lines(schedule),
            "Persistent=true",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )


def _open_systemd_user_dir() -> int:
    path = SYSTEMD_USER_DIR
    if not path.is_absolute():
        raise OmaRunError("The systemd user directory must be absolute.")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    current_fd = os.open(path.anchor or "/", directory_flags)
    try:
        for part in path.parts[1:]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        metadata = os.fstat(current_fd)
        if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o022:
            raise OmaRunError(
                f"Unsafe systemd user directory ownership or permissions: {SYSTEMD_USER_DIR}"
            )
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _read_unit_at(directory_fd: int, name: str) -> tuple[os.stat_result, bytes] | None:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise OmaRunError(f"Refusing symlink collision at {SYSTEMD_USER_DIR / name}") from exc
        raise
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid():
            raise OmaRunError(f"Refusing unowned unit collision at {SYSTEMD_USER_DIR / name}")
        chunks = []
        remaining = UNIT_READ_LIMIT + 1
        while remaining:
            chunk = os.read(fd, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > UNIT_READ_LIMIT:
            raise OmaRunError(f"Refusing oversized unit collision at {SYSTEMD_USER_DIR / name}")
        return metadata, content
    finally:
        os.close(fd)


def _renameat2(
    directory_fd: int, source: str, destination: str, flags: int
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    if function is None:
        raise OmaRunError("This system does not provide atomic renameat2 unit operations.")
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    result = function(
        directory_fd,
        os.fsencode(source),
        directory_fd,
        os.fsencode(destination),
        flags,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            f"{source} -> {destination}",
        )


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _legacy_contents(task: dict[str, Any] | None, kind: str) -> set[bytes]:
    if not task:
        return set()
    if kind == "service":
        return {_legacy_service_content(task).encode("utf-8")}
    schedule = _normalize_schedule(task.get("schedule"))
    if schedule["enabled"]:
        return {_legacy_timer_content(task).encode("utf-8")}
    return set()


def _verify_unit_at(
    directory_fd: int,
    task_id: str,
    kind: str,
    *,
    legacy_task: dict[str, Any] | None = None,
) -> os.stat_result | None:
    name = _service_name(task_id) if kind == "service" else _timer_name(task_id)
    result = _read_unit_at(directory_fd, name)
    if result is None:
        return None
    metadata, content = result
    expected_marker = (_unit_marker(task_id, kind) + "\n").encode("utf-8")
    if content.startswith(expected_marker) or content in _legacy_contents(legacy_task, kind):
        return metadata
    raise OmaRunError(
        f"Refusing foreign unit collision at {SYSTEMD_USER_DIR / name}; "
        "move the file aside or restore the canonical OmaRun unit first."
    )


def _write_unit_at(
    directory_fd: int,
    task: dict[str, Any],
    kind: str,
    content: str,
    *,
    legacy_task: dict[str, Any] | None = None,
) -> None:
    task_id = task["id"]
    name = _service_name(task_id) if kind == "service" else _timer_name(task_id)
    existing = _verify_unit_at(
        directory_fd, task_id, kind, legacy_task=legacy_task
    )
    temp_name = f".{name}.tmp-{secrets.token_hex(8)}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    temp_fd = os.open(temp_name, flags, 0o644, dir_fd=directory_fd)
    preserve_temp = False
    try:
        with os.fdopen(temp_fd, "wb") as output:
            output.write(content.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        new_metadata = os.stat(temp_name, dir_fd=directory_fd, follow_symlinks=False)
        if existing is None:
            try:
                os.link(
                    temp_name,
                    name,
                    src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise OmaRunError(
                    f"Refusing concurrent unit collision at {SYSTEMD_USER_DIR / name}"
                ) from exc
            os.unlink(temp_name, dir_fd=directory_fd)
        else:
            try:
                _renameat2(directory_fd, temp_name, name, RENAME_EXCHANGE)
            except OSError as exc:
                raise OmaRunError(
                    f"Unit changed during update: {SYSTEMD_USER_DIR / name}"
                ) from exc
            swapped_metadata = os.stat(
                temp_name, dir_fd=directory_fd, follow_symlinks=False
            )
            if not _same_inode(swapped_metadata, existing):
                current_metadata = os.stat(
                    name, dir_fd=directory_fd, follow_symlinks=False
                )
                if not _same_inode(current_metadata, new_metadata):
                    preserve_temp = True
                    raise OmaRunError(
                        f"Unit changed during atomic rollback: {SYSTEMD_USER_DIR / name}; "
                        f"the displaced entry remains at {SYSTEMD_USER_DIR / temp_name}."
                    )
                _renameat2(directory_fd, temp_name, name, RENAME_EXCHANGE)
                raise OmaRunError(f"Unit changed during update: {SYSTEMD_USER_DIR / name}")
            os.unlink(temp_name, dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        if not preserve_temp:
            try:
                os.unlink(temp_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass


def _remove_unit_at(
    directory_fd: int,
    task: dict[str, Any],
    kind: str,
    *,
    legacy_task: dict[str, Any] | None = None,
) -> bool:
    task_id = task["id"]
    name = _service_name(task_id) if kind == "service" else _timer_name(task_id)
    existing = _verify_unit_at(
        directory_fd, task_id, kind, legacy_task=legacy_task or task
    )
    if existing is None:
        return False
    quarantine_name = f".{name}.remove-{secrets.token_hex(8)}"
    try:
        _renameat2(directory_fd, name, quarantine_name, RENAME_NOREPLACE)
    except OSError as exc:
        raise OmaRunError(f"Unit changed during removal: {SYSTEMD_USER_DIR / name}") from exc
    quarantined = os.stat(
        quarantine_name, dir_fd=directory_fd, follow_symlinks=False
    )
    if not _same_inode(quarantined, existing):
        try:
            _renameat2(directory_fd, quarantine_name, name, RENAME_NOREPLACE)
        except OSError as exc:
            raise OmaRunError(
                f"Unit changed during atomic rollback: {SYSTEMD_USER_DIR / name}; "
                f"the displaced entry remains at {SYSTEMD_USER_DIR / quarantine_name}."
            ) from exc
        raise OmaRunError(f"Unit changed during removal: {SYSTEMD_USER_DIR / name}")
    os.unlink(quarantine_name, dir_fd=directory_fd)
    os.fsync(directory_fd)
    return True


def _preflight_units(
    directory_fd: int,
    task: dict[str, Any],
    *,
    legacy_task: dict[str, Any] | None = None,
) -> None:
    task_id = task["id"]
    _verify_unit_at(directory_fd, task_id, "service", legacy_task=legacy_task)
    _verify_unit_at(directory_fd, task_id, "timer", legacy_task=legacy_task)


def _write_service(
    task: dict[str, Any],
    directory_fd: int,
    *,
    legacy_task: dict[str, Any] | None = None,
) -> None:
    _write_unit_at(
        directory_fd,
        task,
        "service",
        _service_content(task),
        legacy_task=legacy_task,
    )


def _write_or_remove_timer(
    task: dict[str, Any],
    directory_fd: int,
    *,
    legacy_task: dict[str, Any] | None = None,
) -> None:
    task_id = task["id"]
    schedule = _normalize_schedule(task.get("schedule"))
    if not schedule["enabled"]:
        if _verify_unit_at(
            directory_fd, task_id, "timer", legacy_task=legacy_task
        ) is not None:
            _run_systemctl(["disable", "--now", _timer_name(task_id)], check=False)
            _remove_unit_at(
                directory_fd, task, "timer", legacy_task=legacy_task
            )
            _daemon_reload()
        return
    _write_unit_at(
        directory_fd,
        task,
        "timer",
        _timer_content(task),
        legacy_task=legacy_task,
    )
    _daemon_reload()
    _run_systemctl(["enable", _timer_name(task_id)])
    _run_systemctl(["restart", _timer_name(task_id)])


def _sync_systemd(
    task: dict[str, Any], *, legacy_task: dict[str, Any] | None = None
) -> None:
    directory_fd = _open_systemd_user_dir()
    try:
        _preflight_units(directory_fd, task, legacy_task=legacy_task)
        _write_service(task, directory_fd, legacy_task=legacy_task)
        _daemon_reload()
        _write_or_remove_timer(
            task, directory_fd, legacy_task=legacy_task
        )
    finally:
        os.close(directory_fd)


def _remove_systemd_files(task: dict[str, Any]) -> None:
    task_id = task["id"]
    directory_fd = _open_systemd_user_dir()
    try:
        service_owned = _verify_unit_at(
            directory_fd, task_id, "service", legacy_task=task
        ) is not None
        timer_owned = _verify_unit_at(
            directory_fd, task_id, "timer", legacy_task=task
        ) is not None
        if service_owned:
            _run_systemctl(["stop", _service_name(task_id)], check=False)
        if timer_owned:
            _run_systemctl(["disable", "--now", _timer_name(task_id)], check=False)
        if service_owned:
            _remove_unit_at(directory_fd, task, "service", legacy_task=task)
        if timer_owned:
            _remove_unit_at(directory_fd, task, "timer", legacy_task=task)
        if service_owned or timer_owned:
            _daemon_reload()
    finally:
        os.close(directory_fd)


def _read_status(task_id: str) -> dict[str, Any]:
    status_file = task_state_dir(task_id) / "status.json"
    if status_file.exists():
        return json.loads(status_file.read_text(encoding="utf-8"))
    return {
        "status": "never",
        "message": "Never executed",
        "exitCode": None,
        "startedAt": None,
        "finishedAt": None,
        "durationMs": None,
    }


def _read_log(task_id: str, prefer_running: bool = True) -> dict[str, Any]:
    state_dir = task_state_dir(task_id)
    last_log = state_dir / "last.log"
    if prefer_running:
        data, truncated = read_active_log(state_dir)
        if data:
            return {
                "source": "current.log",
                "text": data.decode("utf-8", errors="replace"),
                "truncated": truncated,
            }
    if last_log.exists():
        data, truncated = read_file_tail(last_log, LOG_STORAGE_BYTES)
        if truncated:
            marker = b"[... earlier output omitted by OmaRun ...]\n"
            data = marker + data[-(LOG_STORAGE_BYTES - len(marker)):]
        return {
            "source": "last.log",
            "text": data.decode("utf-8", errors="replace"),
            "truncated": truncated,
        }
    return {"source": "", "text": "", "truncated": False}


def _bounded_log_response(payload: dict[str, Any]) -> bytes:
    def encode(candidate: dict[str, Any]) -> bytes:
        return json.dumps(candidate, ensure_ascii=False).encode("utf-8") + b"\n"

    rendered = encode(payload)
    if len(rendered) <= LOG_RESPONSE_BYTES:
        return rendered
    text = str(payload.get("text", ""))
    base = {**payload, "truncated": True}
    low = 0
    high = len(text)
    best = RESPONSE_MARKER
    while low <= high:
        midpoint = (low + high) // 2
        candidate_text = RESPONSE_MARKER + (text[-midpoint:] if midpoint else "")
        candidate = {**base, "text": candidate_text}
        encoded = encode(candidate)
        if len(encoded) <= LOG_RESPONSE_BYTES:
            best = candidate_text
            low = midpoint + 1
        else:
            high = midpoint - 1
    rendered = encode({**base, "text": best})
    if len(rendered) > LOG_RESPONSE_BYTES:
        raise OmaRunError("The bounded log response could not be encoded safely.")
    return rendered


def _verify_task_unit(task: dict[str, Any], kind: str, *, required: bool) -> bool:
    directory_fd = _open_systemd_user_dir()
    try:
        result = _verify_unit_at(
            directory_fd, task["id"], kind, legacy_task=task
        )
    finally:
        os.close(directory_fd)
    if result is None and required:
        unit_name = _service_name(task["id"]) if kind == "service" else _timer_name(task["id"])
        raise OmaRunError(
            f"Owned unit is missing: {unit_name}. Edit and save the task to recreate it."
        )
    return result is not None


def _next_run(task: dict[str, Any]) -> str | None:
    schedule = _normalize_schedule(task.get("schedule"))
    if not schedule["enabled"]:
        return None
    task_id = task["id"]
    _verify_task_unit(task, "timer", required=True)
    result = _run_systemctl(
        ["show", _timer_name(task_id), "-p", "NextElapseUSecRealtime", "--value"],
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def cmd_list(_args: argparse.Namespace) -> None:
    tasks = load_tasks()
    enriched = []
    for task in tasks:
        task_id = task["id"]
        status = _read_status(task_id)
        _verify_task_unit(task, "service", required=True)
        running = _run_systemctl(["is-active", _service_name(task_id)], check=False).returncode == 0
        enriched.append(
            {
                **task,
                "running": running,
                "lastStatus": status,
                "nextRun": _next_run(task),
            }
        )
    print(json.dumps({"tasks": enriched}, ensure_ascii=False, indent=2))


def cmd_add(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    task_id = make_task_id()
    schedule = _normalize_schedule(json.loads(args.schedule) if args.schedule else None)
    task = {
        "id": task_id,
        "name": args.name,
        "command": args.command,
        "arguments": args.arguments or "",
        "workingDirectory": args.working_directory or "",
        "timeoutSeconds": args.timeout_seconds or 0,
        "env": json.loads(args.env) if args.env else {},
        "schedule": schedule,
    }
    tasks.append(task)
    save_tasks(tasks)
    try:
        _sync_systemd(task)
    except Exception:
        tasks.pop()
        save_tasks(tasks)
        try:
            _remove_systemd_files(task)
        except Exception:
            pass
        raise
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_update(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    validate_task_id(args.id)
    task = get_task(tasks, args.id)
    original_task = copy.deepcopy(task)
    if args.name is not None:
        task["name"] = args.name
    if args.command is not None:
        task["command"] = args.command
    if args.arguments is not None:
        task["arguments"] = args.arguments
    if args.working_directory is not None:
        task["workingDirectory"] = args.working_directory
    if args.timeout_seconds is not None:
        task["timeoutSeconds"] = args.timeout_seconds
    if args.env is not None:
        task["env"] = json.loads(args.env)
    if args.schedule is not None:
        task["schedule"] = _normalize_schedule(json.loads(args.schedule))
    save_tasks(tasks)
    try:
        _sync_systemd(task, legacy_task=original_task)
    except Exception:
        task.clear()
        task.update(original_task)
        save_tasks(tasks)
        _sync_systemd(task, legacy_task=original_task)
        raise
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_delete(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    validate_task_id(args.id)
    task = get_task(tasks, args.id)
    task_id = task["id"]

    _remove_systemd_files(task)

    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    shutil.rmtree(task_state_dir(task_id), ignore_errors=True)
    print(json.dumps({"deleted": task_id}, ensure_ascii=False, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    task = get_task(load_tasks(), args.id)
    _verify_task_unit(task, "service", required=True)
    running = _run_systemctl(["is-active", _service_name(args.id)], check=False).returncode == 0
    if running:
        raise OmaRunError("Task is already running.")
    _run_systemctl(["start", _service_name(args.id)])
    print(json.dumps({"started": args.id}, ensure_ascii=False, indent=2))


def cmd_stop(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    task = get_task(load_tasks(), args.id)
    _verify_task_unit(task, "service", required=True)
    _run_systemctl(["stop", _service_name(args.id)], check=False)
    print(json.dumps({"stopped": args.id}, ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    task = get_task(load_tasks(), args.id)
    _verify_task_unit(task, "service", required=True)
    running = _run_systemctl(["is-active", _service_name(args.id)], check=False).returncode == 0
    print(
        json.dumps(
            {
                "id": args.id,
                "running": running,
                "lastStatus": _read_status(args.id),
                "nextRun": _next_run(task),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_log(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    task = get_task(load_tasks(), args.id)
    _verify_task_unit(task, "service", required=True)
    running = _run_systemctl(["is-active", _service_name(args.id)], check=False).returncode == 0
    sys.stdout.buffer.write(
        _bounded_log_response(
            {"id": args.id, "running": running, **_read_log(args.id, prefer_running=running)}
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OmaRun control CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--command", required=True)
    p_add.add_argument("--arguments")
    p_add.add_argument("--working-directory")
    p_add.add_argument("--timeout-seconds", type=int, default=0)
    p_add.add_argument("--env", help='JSON object, e.g. {"FOO":"bar"}')
    p_add.add_argument("--schedule", help='JSON object, e.g. {"enabled":true,"mode":"every-hours","interval":6}')
    p_add.set_defaults(func=cmd_add)

    p_update = sub.add_parser("update")
    p_update.add_argument("--id", required=True)
    p_update.add_argument("--name")
    p_update.add_argument("--command")
    p_update.add_argument("--arguments")
    p_update.add_argument("--working-directory")
    p_update.add_argument("--timeout-seconds", type=int)
    p_update.add_argument("--env")
    p_update.add_argument("--schedule")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete")
    p_delete.add_argument("--id", required=True)
    p_delete.set_defaults(func=cmd_delete)

    p_run = sub.add_parser("run")
    p_run.add_argument("--id", required=True)
    p_run.set_defaults(func=cmd_run)

    p_stop = sub.add_parser("stop")
    p_stop.add_argument("--id", required=True)
    p_stop.set_defaults(func=cmd_stop)

    p_status = sub.add_parser("status")
    p_status.add_argument("--id", required=True)
    p_status.set_defaults(func=cmd_status)

    p_log = sub.add_parser("log")
    p_log.add_argument("--id", required=True)
    p_log.set_defaults(func=cmd_log)

    return parser


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
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OmaRunError as exc:
        print(f"error: {exc}")
        raise SystemExit(2)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr.strip() or exc.stdout.strip() or str(exc))
        raise SystemExit(exc.returncode or 1)
