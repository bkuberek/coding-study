"""What the Go and Rust runners share about their generated builds in `.cs/build/<lang>`
(docs/specs/runners.md#go-build-details, #rust-build-details).

Two `cstudy` processes may build the same problem at once (a watcher and a verify), so the
generation and the build hold an exclusive lock, and each process runs its own copy of the built
binary, which no other build overwrites. Generated files are written only when their content
changes: Cargo fingerprints sources by modification time, and editors and watchers notice writes.
"""

import fcntl
import os
import shutil
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def exclusive(lock_file: Path) -> Generator[None]:
    """Holds an exclusive lock on `lock_file` (created when missing)."""
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def write_if_changed(path: Path, text: str) -> None:
    """Writes `text` unless the file already holds it, keeping its timestamp."""
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def private_copy(binary: Path, directory: Path) -> Path:
    """A copy of `binary` in `directory` that only this process (and thread) runs, so a later
    build by another process can never replace the file this one is about to start. Copies of
    processes that ended are removed."""
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.iterdir():
        if not _owner_alive(stale.name):
            stale.unlink(missing_ok=True)
    copy = directory / f"{os.getpid()}-{threading.get_ident()}"
    temporary = copy.with_name(f".{copy.name}.tmp")
    shutil.copyfile(binary, temporary)
    temporary.chmod(0o755)
    temporary.replace(copy)
    return copy


def _owner_alive(name: str) -> bool:
    """Whether the process that owns a private copy `<pid>-<thread>` still runs."""
    pid, _, _ = name.partition("-")
    if not pid.isdigit():
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def relative(path: Path, start: Path) -> str:
    """`path` relative to `start`, in POSIX form."""
    return Path(os.path.relpath(path, start)).as_posix()
