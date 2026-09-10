import argparse
import copy
import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from storage import (
    OmaRunError,
    SYSTEMD_USER_DIR,
    get_task,
    load_tasks,
    make_task_id,
    save_tasks,
    task_state_dir,
    validate_task_id,
)


def _service_name(task_id: str) -> str:
    return f"omarun-{task_id}.service"


def _timer_name(task_id: str) -> str:
    return f"omarun-{task_id}.timer"


def _service_path(task_id: str) -> Path:
    return SYSTEMD_USER_DIR / _service_name(task_id)


def _timer_path(task_id: str) -> Path:
    return SYSTEMD_USER_DIR / _timer_name(task_id)


def _run_systemctl(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["systemctl", "--user", *args]
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


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
        return [f"OnUnitActiveSec={schedule['interval']}min"]
    if mode == "every-hours":
        return [f"OnUnitActiveSec={schedule['interval']}h"]
    if mode == "every-days":
        return [f"OnUnitActiveSec={schedule['interval']}d"]
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


def _write_service(task: dict[str, Any]) -> None:
    task_id = task["id"]
    runner_path = Path(__file__).resolve().parent / "runner.py"
    service_content = "\n".join(
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
    _service_path(task_id).write_text(service_content, encoding="utf-8")


def _write_or_remove_timer(task: dict[str, Any]) -> None:
    task_id = task["id"]
    timer_file = _timer_path(task_id)
    schedule = _normalize_schedule(task.get("schedule"))
    if not schedule["enabled"]:
        if timer_file.exists():
            _run_systemctl(["disable", "--now", _timer_name(task_id)], check=False)
            timer_file.unlink()
            _daemon_reload()
        return

    lines = _schedule_to_timer_lines(schedule)
    timer_content = "\n".join(
        [
            "[Unit]",
            f"Description=OmaRun schedule for {task['name']}",
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
    timer_file.write_text(timer_content, encoding="utf-8")
    _daemon_reload()
    _run_systemctl(["enable", "--now", _timer_name(task_id)])


def _sync_systemd(task: dict[str, Any]) -> None:
    _write_service(task)
    _daemon_reload()
    _write_or_remove_timer(task)


def _remove_systemd_files(task_id: str) -> None:
    _run_systemctl(["stop", _service_name(task_id)], check=False)
    _run_systemctl(["disable", "--now", _timer_name(task_id)], check=False)
    for path in (_service_path(task_id), _timer_path(task_id)):
        if path.exists():
            path.unlink()
    _daemon_reload()


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
    current_log = state_dir / "current.log"
    last_log = state_dir / "last.log"
    if prefer_running and current_log.exists():
        return {"source": "current.log", "text": current_log.read_text(encoding="utf-8")}
    if last_log.exists():
        return {"source": "last.log", "text": last_log.read_text(encoding="utf-8")}
    return {"source": "", "text": ""}


def _next_run(task_id: str) -> str | None:
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
        running = _run_systemctl(["is-active", _service_name(task_id)], check=False).returncode == 0
        enriched.append(
            {
                **task,
                "running": running,
                "lastStatus": status,
                "nextRun": _next_run(task_id),
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
        _remove_systemd_files(task_id)
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
        _sync_systemd(task)
    except Exception:
        task.clear()
        task.update(original_task)
        save_tasks(tasks)
        _sync_systemd(task)
        raise
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_delete(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    validate_task_id(args.id)
    task = get_task(tasks, args.id)
    task_id = task["id"]

    _remove_systemd_files(task_id)

    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    shutil.rmtree(task_state_dir(task_id), ignore_errors=True)
    print(json.dumps({"deleted": task_id}, ensure_ascii=False, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    running = _run_systemctl(["is-active", _service_name(args.id)], check=False).returncode == 0
    if running:
        raise OmaRunError("Task is already running.")
    _run_systemctl(["start", _service_name(args.id)])
    print(json.dumps({"started": args.id}, ensure_ascii=False, indent=2))


def cmd_stop(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    _run_systemctl(["stop", _service_name(args.id)], check=False)
    print(json.dumps({"stopped": args.id}, ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    running = _run_systemctl(["is-active", _service_name(args.id)], check=False).returncode == 0
    print(
        json.dumps(
            {
                "id": args.id,
                "running": running,
                "lastStatus": _read_status(args.id),
                "nextRun": _next_run(args.id),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_log(args: argparse.Namespace) -> None:
    validate_task_id(args.id)
    print(json.dumps({"id": args.id, **_read_log(args.id)}, ensure_ascii=False, indent=2))


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


def main() -> int:
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
