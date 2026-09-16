import json
import os
import pwd
import re
import stat
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "omarun"
STATE_DIR = Path.home() / ".local" / "state" / "omarun"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
TASKS_FILE = CONFIG_DIR / "tasks.json"

PYTHON_EXECUTABLE = Path("/usr/bin/python3")
SYSTEMCTL_EXECUTABLE = Path("/usr/bin/systemctl")
ENV_EXECUTABLE = Path("/usr/bin/env")

LOG_SEGMENT_BYTES = 2 * 1024 * 1024
LOG_STORAGE_BYTES = 2 * LOG_SEGMENT_BYTES
LOG_RESPONSE_BYTES = 512 * 1024

TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


class OmaRunError(Exception):
    pass


@dataclass
class Task:
    id: str
    name: str
    command: str
    arguments: str = ""
    working_directory: str = ""
    timeout_seconds: int = 0
    env: dict[str, str] | None = None
    schedule: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "arguments": self.arguments,
            "workingDirectory": self.working_directory,
            "timeoutSeconds": self.timeout_seconds,
            "env": self.env or {},
            "schedule": self.schedule or {"enabled": False},
        }


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "tasks").mkdir(parents=True, exist_ok=True)


def user_identity() -> pwd.struct_passwd:
    return pwd.getpwuid(os.geteuid())


def control_environment() -> dict[str, str]:
    """Return the fixed environment used by OmaRun's control-plane tools."""
    identity = user_identity()
    runtime_dir = f"/run/user/{os.geteuid()}"
    return {
        "HOME": identity.pw_dir,
        "USER": identity.pw_name,
        "LOGNAME": identity.pw_name,
        "SHELL": identity.pw_shell or "/bin/sh",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "XDG_RUNTIME_DIR": runtime_dir,
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime_dir}/bus",
    }


def verify_trusted_executable(path: Path) -> Path:
    """Resolve a root-managed executable and reject writable replacements."""
    if not path.is_absolute():
        raise OmaRunError(f"Executable path must be absolute: {path}")
    try:
        resolved = path.resolve(strict=True)
        metadata = resolved.stat()
    except OSError as exc:
        raise OmaRunError(f"Required executable is unavailable: {path}") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
        raise OmaRunError(f"Required executable is not root-managed: {path}")
    if not os.access(resolved, os.X_OK):
        raise OmaRunError(f"Required executable is not executable: {path}")
    return resolved


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", text=True)
    try:
        with open(fd, "w", encoding="utf-8") as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
        Path(tmp_path).replace(path)
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink(missing_ok=True)


def load_tasks() -> list[dict[str, Any]]:
    ensure_dirs()
    if not TASKS_FILE.exists():
        _atomic_write_json(TASKS_FILE, {"tasks": []})
    with TASKS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        raise OmaRunError(f"Invalid tasks.json format at {TASKS_FILE}")
    return tasks


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    _atomic_write_json(TASKS_FILE, {"tasks": tasks})


def validate_task_id(task_id: str) -> None:
    if not TASK_ID_RE.match(task_id):
        raise OmaRunError(
            "Invalid task id. Expected 3-64 chars with lowercase letters, numbers and dashes."
        )


def make_task_id() -> str:
    return f"task-{uuid.uuid4().hex[:12]}"


def get_task(tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
    for task in tasks:
        if task.get("id") == task_id:
            return task
    raise OmaRunError(f"Task not found: {task_id}")


def task_state_dir(task_id: str) -> Path:
    validate_task_id(task_id)
    path = STATE_DIR / "tasks" / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path
