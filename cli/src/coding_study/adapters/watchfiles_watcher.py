"""Waits for saves of the user's code, for `cstudy test --watch` (docs/specs/cli.md#cstudy-test),
and for changes in the folders the web UI's notifications cover
(docs/specs/web-ui.md#notifications).

A single file is watched through its directory, filtered to that file, because editors often
save by writing a new file and renaming it over the old one. A directory, such as a JVM package or
a project folder, is watched with its tracked files only: the `.venv` link, `node_modules` and
caches are not (docs/specs/installation-and-workspaces.md#project-folders). A burst yields only
when the watched content differs from the last time, so replayed file-system events and saves that
change nothing do not re-run the tests.
"""

import asyncio
import hashlib
import threading
from collections.abc import AsyncGenerator, Callable, Iterable, Iterator, Sequence
from pathlib import Path

import watchfiles

from coding_study.adapters.project_folders import tracked_files
from coding_study.application.attempt_changes import WatchedFolder
from coding_study.domain.workspace_projects import is_untracked

DEBOUNCE_MS = 150


class WatchfilesWatcher:
    """`ChangeWatcher`, and the folder watch of the web UI's notifications; `stop_event` ends
    every `changes` watch when set (tests)."""

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

    async def folder_changes(
        self, root: Path, folders: Sequence[WatchedFolder], stop_event: asyncio.Event
    ) -> AsyncGenerator[None]:
        """Yields once per debounced burst of changes to what `folders` cover, relative to
        `root`, until `stop_event` is set; whether the content changed is the caller's to
        compare. One watch covers the recursive folders and another the others, since a watch is
        recursive or not as a whole."""
        burst = asyncio.Event()
        watches = [
            asyncio.create_task(_signal_bursts(root, group, recursive, stop_event, burst))
            for recursive in (True, False)
            if (group := [folder for folder in folders if folder.recursive is recursive])
        ]
        try:
            while not stop_event.is_set() and not all(watch.done() for watch in watches):
                await _burst_or_end(burst, stop_event, watches)
                if burst.is_set():
                    burst.clear()
                    yield None
            for watch in watches:
                if watch.done():
                    watch.result()  # raises what ended a watch, such as a folder that went
        finally:
            for watch in watches:
                watch.cancel()
            await asyncio.gather(*watches, return_exceptions=True)


async def _signal_bursts(
    root: Path,
    folders: Iterable[WatchedFolder],
    recursive: bool,
    stop_event: asyncio.Event,
    burst: asyncio.Event,
) -> None:
    """Sets `burst` after each burst of changes, until `stop_event` is set or the task is
    cancelled; watchfiles' watch blocks, so it runs in a thread of its own, which ends within
    a step of either."""
    loop = asyncio.get_running_loop()
    paths = {(root / folder.path).resolve(): folder for folder in folders}
    stop = threading.Event()

    def watch() -> None:
        for _ in watchfiles.watch(
            *paths,
            watch_filter=lambda _change, changed: _covered(paths, Path(changed).resolve()),
            debounce=DEBOUNCE_MS,
            recursive=recursive,
            stop_event=stop,
        ):
            loop.call_soon_threadsafe(burst.set)

    watching = asyncio.ensure_future(asyncio.to_thread(watch))
    stopping = asyncio.ensure_future(stop_event.wait())
    try:
        await asyncio.wait([watching, stopping], return_when=asyncio.FIRST_COMPLETED)
    finally:
        stop.set()
        stopping.cancel()
        await asyncio.wait([watching])
    watching.result()


def _covered(folders: dict[Path, WatchedFolder], changed: Path) -> bool:
    """Whether a folder holds the file `changed`: directly, or in a subfolder of a recursive
    one; by its name when the folder names its entries, else when it is not untracked. A
    directory is no file: a change of its files reports them."""
    if changed.is_dir():
        return False
    return any(
        changed.is_relative_to(directory) and _counts(folder, changed.relative_to(directory))
        for directory, folder in folders.items()
    )


def _counts(folder: WatchedFolder, relative: Path) -> bool:
    if not relative.parts or (not folder.recursive and len(relative.parts) > 1):
        return False
    if folder.names:
        return relative.name in folder.names
    return not is_untracked(relative.as_posix())


async def _burst_or_end(
    burst: asyncio.Event, stop_event: asyncio.Event, watches: Iterable["asyncio.Task[None]"]
) -> None:
    """Returns once a burst came, the watching should stop, or a watch ended."""
    waits = [asyncio.create_task(burst.wait()), asyncio.create_task(stop_event.wait())]
    try:
        await asyncio.wait([*waits, *watches], return_when=asyncio.FIRST_COMPLETED)
    finally:
        for wait in waits:
            wait.cancel()


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
