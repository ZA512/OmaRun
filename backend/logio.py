import os
import stat
import tempfile
from pathlib import Path
from typing import BinaryIO

from storage import LOG_SEGMENT_BYTES, LOG_STORAGE_BYTES


OMITTED_MARKER = b"[... earlier output omitted by OmaRun ...]\n"
RESPONSE_MARKER = "[... log response truncated by OmaRun ...]\n"


def _open_regular_for_read(path: Path) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags)


def read_file_tail(path: Path, limit: int) -> tuple[bytes, bool]:
    """Read at most limit bytes from a regular file, preferring its newest bytes."""
    if limit <= 0:
        return b"", path.exists()
    try:
        fd = _open_regular_for_read(path)
    except FileNotFoundError:
        return b"", False
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError(f"Log is not a regular file: {path}")
        truncated = metadata.st_size > limit
        if truncated:
            os.lseek(fd, metadata.st_size - limit, os.SEEK_SET)
        chunks = []
        remaining = limit
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks), truncated
    finally:
        os.close(fd)


def read_active_log(state_dir: Path) -> tuple[bytes, bool]:
    current = state_dir / "current.log"
    rotated = state_dir / "current.log.1"
    truncated_flag = state_dir / "current.log.truncated"
    current_bytes, current_truncated = read_file_tail(current, LOG_STORAGE_BYTES)
    remaining = max(0, LOG_STORAGE_BYTES - len(current_bytes))
    rotated_bytes, rotated_truncated = read_file_tail(rotated, remaining)
    truncated = truncated_flag.exists() or current_truncated or rotated_truncated
    data = rotated_bytes + current_bytes
    if truncated:
        data = OMITTED_MARKER + data
        if len(data) > LOG_STORAGE_BYTES:
            data = OMITTED_MARKER + data[-(LOG_STORAGE_BYTES - len(OMITTED_MARKER)):]
    return data, truncated


def _atomic_write(path: Path, data: bytes) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".tmp-{path.name}-")
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp_path, path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def finalize_active_log(state_dir: Path) -> None:
    data, _truncated = read_active_log(state_dir)
    _atomic_write(state_dir / "last.log", data)
    for name in ("current.log", "current.log.1", "current.log.truncated"):
        (state_dir / name).unlink(missing_ok=True)


class RotatingLogWriter:
    """Drain command output into two fixed-size on-disk segments."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.current_path = state_dir / "current.log"
        self.rotated_path = state_dir / "current.log.1"
        self.truncated_path = state_dir / "current.log.truncated"
        for path in (self.current_path, self.rotated_path, self.truncated_path):
            path.unlink(missing_ok=True)
        self._output = self._open_current()
        self._size = 0

    def _open_current(self) -> BinaryIO:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.current_path, flags, 0o600)
        return os.fdopen(fd, "wb", buffering=0)

    def _rotate(self) -> None:
        self._output.close()
        if self.rotated_path.exists():
            self.rotated_path.unlink()
            self.truncated_path.touch(mode=0o600, exist_ok=True)
        os.replace(self.current_path, self.rotated_path)
        self._output = self._open_current()
        self._size = 0

    def write(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            if self._size == LOG_SEGMENT_BYTES:
                self._rotate()
            available = LOG_SEGMENT_BYTES - self._size
            chunk = view[:available]
            self._output.write(chunk)
            self._size += len(chunk)
            view = view[len(chunk):]

    def close(self) -> None:
        if not self._output.closed:
            self._output.close()
