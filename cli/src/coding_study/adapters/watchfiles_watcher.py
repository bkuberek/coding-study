"""Waits for saves of the user's code, for `cstudy test --watch` (docs/specs/cli.md#cstudy-test).

A single file is watched through its directory, filtered to that file, because editors often
save by writing a new file and renaming it over the old one. A directory, such as a JVM package or
a project folder, is watched with its tracked files only: the `.venv` link, `node_modules` and
caches are not (docs/specs/installation-and-workspaces.md#project-folders). A burst yields only
when the watched content differs from the last time, so replayed file-system events and saves that
change nothing do not re-run the tests.
"""

import hashlib
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import watchfiles

from coding_study.adapters.project_folders import tracked_files
from coding_study.domain.workspace_projects import is_untracked

DEBOUNCE_MS = 150


class WatchfilesWatcher:
    """`ChangeWatcher`; `stop_event` ends every watch when set (tests)."""

    def __init__(self, stop_event: threading.Event | None = None) -> None:
        self._stop_event = stop_event

    def changes(self, path: Path) -> Iterator[None]:
        directory = path if path.is_dir() else path.parent
        accepts = _tracked_in(path) if path.is_dir() else _same_file(path)
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


def _tracked_in(directory: Path) -> Callable[[str], bool]:
    resolved = directory.resolve()

    def accepts(changed: str) -> bool:
        try:
            relative = Path(changed).resolve().relative_to(resolved)
        except ValueError:
            return False
        return not is_untracked(relative.as_posix())

    return accepts


def _same_file(target: Path) -> Callable[[str], bool]:
    resolved = target.resolve()
    return lambda changed: Path(changed).resolve() == resolved


def _content_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in tracked_files(path) if path.is_dir() else [path]:
        digest.update(str(file).encode())
        digest.update(file.read_bytes() if file.is_file() else b"\0missing")
    return digest.hexdigest()
