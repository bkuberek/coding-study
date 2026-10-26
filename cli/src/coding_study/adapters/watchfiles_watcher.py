"""Waits for saves of the user's code, for `cstudy test --watch` (docs/specs/cli.md#cstudy-test).

A single file is watched through its directory, filtered to that file, because editors often
save by writing a new file and renaming it over the old one. A burst yields only when the
watched content differs from the last time, so replayed file-system events and saves that change
nothing do not re-run the tests.
"""

import hashlib
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import watchfiles

DEBOUNCE_MS = 150


class WatchfilesWatcher:
    """`ChangeWatcher`; `stop_event` ends every watch when set (tests)."""

    def __init__(self, stop_event: threading.Event | None = None) -> None:
        self._stop_event = stop_event

    def changes(self, path: Path) -> Iterator[None]:
        directory = path if path.is_dir() else path.parent
        accepts = _anything if path.is_dir() else _same_file(path)
        last = _content_digest(path)
        for _ in watchfiles.watch(
            directory,
            watch_filter=lambda _change, changed: accepts(changed),
            debounce=DEBOUNCE_MS,
            recursive=path.is_dir(),
            stop_event=self._stop_event,
        ):
            current = _content_digest(path)
            if current != last:
                last = current
                yield None


def _anything(_changed: str) -> bool:
    return True


def _same_file(target: Path) -> Callable[[str], bool]:
    resolved = target.resolve()
    return lambda changed: Path(changed).resolve() == resolved


def _content_digest(path: Path) -> str:
    digest = hashlib.sha256()
    files = (
        sorted(entry for entry in path.rglob("*") if entry.is_file()) if path.is_dir() else [path]
    )
    for file in files:
        digest.update(str(file).encode())
        digest.update(file.read_bytes() if file.is_file() else b"\0missing")
    return digest.hexdigest()
