"""Locks on a file that every `cstudy` process of a workspace takes by the same path."""

import fcntl
import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

LOCK_FILE_MODE = 0o644


def _ignore() -> None:
    return None


@contextmanager
def exclusive_lock(path: Path, on_wait: Callable[[], None] = _ignore) -> Generator[None]:
    """Hold an exclusive `flock` on `path`, created when missing, for the `with` block.

    Another process, or another thread of this one, that holds the lock makes this wait: `on_wait`
    runs once, then the call blocks (Ctrl-C still interrupts it). The kernel drops the lock when
    its holder ends, however it ends, so a crash never leaves it held.
    """
    with _flock(path, fcntl.LOCK_EX, on_wait):
        yield


@contextmanager
def shared_lock(path: Path, on_wait: Callable[[], None] = _ignore) -> Generator[None]:
    """Like `exclusive_lock`, but any number of holders share it; it waits only for an
    exclusive holder, and an exclusive lock waits for every shared holder."""
    with _flock(path, fcntl.LOCK_SH, on_wait):
        yield


@contextmanager
def _flock(path: Path, operation: int, on_wait: Callable[[], None]) -> Generator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, LOCK_FILE_MODE)
    try:
        try:
            fcntl.flock(descriptor, operation | fcntl.LOCK_NB)
        except BlockingIOError:
            on_wait()
            fcntl.flock(descriptor, operation)
        yield
    finally:
        os.close(descriptor)
