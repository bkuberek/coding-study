"""Notifications (docs/specs/web-ui.md#notifications): one stream per tab of what changed, wherever
it changed: the files of the attempts in progress, their manifests and statements, progress.db,
and the server's runs and jobs.

A watch of the folders those files live in wakes on each burst of file-system events; a snapshot
of what they hold then gives the changes by content (`application.attempt_changes`), read on the
worker as every use case is. The server numbers its notices and keeps the last REPLAYED, so a
stream that comes back with `Last-Event-ID` gets what it missed. Every stream ends when the server
stops: none would end on its own, and the server waits for its open responses.
"""

import asyncio
import json
import sys
from collections import deque
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Mapping, Sequence
from contextlib import aclosing, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.application.attempt_changes import (
    AttemptChanged,
    FileChanged,
    ProgressChanged,
    WatchedFolder,
    WorkspaceChange,
    WorkspaceSnapshot,
    workspace_changes,
)
from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.web.runs import KEEP_ALIVE, Child, ChildKind, Message

REPLAYED = 100


@dataclass(frozen=True, slots=True)
class NotificationTiming:
    keep_alive_s: float = 15.0
    """How long a stream stays silent before a comment line keeps the connection open."""
    progress_interval_s: float = 0.25
    """At most one `progress_changed` per interval; one that comes within it waits for its end."""
    retry_s: float = 1.0
    """How long a watch of the workspace that failed waits before it starts again."""


class Notifications:
    """The server's notices, numbered from 0, and the streams that read them."""

    def __init__(self, timing: NotificationTiming | None = None) -> None:
        self.timing = timing or NotificationTiming()
        self.stopped = asyncio.Event()
        """Set once the server stops: every stream ends."""
        self._kept: deque[Message] = deque(maxlen=REPLAYED)
        self._count = 0
        self._wakeup = asyncio.Event()
        self._progress_sent: float | None = None
        self._progress_due: asyncio.TimerHandle | None = None

    def publish(self, event: str, document: Mapping[str, JsonValue]) -> None:
        if self.stopped.is_set():
            return
        self._kept.append(Message(event, json.dumps(document)))
        self._count += 1
        self._notify()

    def notice(self, change: WorkspaceChange) -> None:
        match change:
            case FileChanged(attempt_id, path, sha256):
                document = {"attempt_id": attempt_id, "path": path, "sha256": sha256}
                self.publish("file_changed", document)
            case AttemptChanged(attempt_id, slug):
                self.publish("attempt_changed", {"attempt_id": attempt_id, "slug": slug})
            case ProgressChanged():
                self.progress_changed()

    def progress_changed(self) -> None:
        """`progress_changed` now, or once the interval since the last one ends; changes within
        it share that one."""
        if self._progress_due is not None:
            return
        loop = asyncio.get_running_loop()
        sent = self._progress_sent
        wait = 0.0 if sent is None else sent + self.timing.progress_interval_s - loop.time()
        if wait <= 0:
            self._send_progress()
        else:
            self._progress_due = loop.call_later(wait, self._send_progress)

    def stop(self) -> None:
        """Ends every stream, and the watch of the workspace."""
        if self._progress_due is not None:
            self._progress_due.cancel()
        self.stopped.set()
        self._notify()

    def frames(self, after: int | None) -> AsyncIterator[str]:
        """The notices after the one numbered `after` that are still kept (from this call on for
        None), the live ones, a comment line whenever the stream would stay silent too long; it
        ends once the server stops."""
        return self._frames_from(self._count if after is None else min(after + 1, self._count))

    async def _frames_from(self, index: int) -> AsyncIterator[str]:
        while True:
            wakeup = self._wakeup
            index = max(index, self._count - len(self._kept))
            while index < self._count:
                yield self._kept[index - self._count].frame(index)
                index += 1
            if self.stopped.is_set():
                return
            try:
                await asyncio.wait_for(wakeup.wait(), self.timing.keep_alive_s)
            except TimeoutError:
                yield KEEP_ALIVE

    def _send_progress(self) -> None:
        self._progress_due = None
        self._progress_sent = asyncio.get_running_loop().time()
        self.publish("progress_changed", {})

    def _notify(self) -> None:
        """Wakes every stream waiting for a notice."""
        self._wakeup.set()
        self._wakeup = asyncio.Event()


class ChildNotices:
    """Tells every tab when a run or a job starts and ends, and ends the streams as the server
    stops, which it does by stopping its runs and jobs first."""

    def __init__(self, notifications: Notifications) -> None:
        self._notifications = notifications

    def started(self, child: Child) -> None:
        self._notifications.publish(f"{child.kind}_started", _child_document(child))

    def ended(self, child: Child) -> None:
        exit_code = child.closed.exit_code if child.closed else None
        document = {**_child_document(child), "exit_code": exit_code}
        self._notifications.publish(f"{child.kind}_ended", document)

    def stopping(self) -> None:
        self._notifications.stop()


def _child_document(child: Child) -> dict[str, JsonValue]:
    command = child.start.command
    if child.kind is ChildKind.RUN:
        return {"run_id": child.id, "attempt_id": child.start.attempt_id, "command": command}
    return {"job_id": child.id, "command": command}


class FolderWatcher(Protocol):
    def folder_changes(
        self, root: Path, folders: Sequence[WatchedFolder], stop_event: asyncio.Event
    ) -> AsyncGenerator[None]:
        """Yields once per debounced burst of changes to what `folders` cover, relative to
        `root`, until `stop_event` is set (`WatchfilesWatcher`)."""
        ...


type TakeSnapshot = Callable[[WorkspaceSnapshot | None], Awaitable[WorkspaceSnapshot]]
"""A snapshot of the workspace, given the one before, which spares a read of progress.db while
it is unchanged."""


class WorkspaceWatch:
    """Watches the folders of the latest snapshot and publishes what each burst of events changed.
    A snapshot whose folders differ starts the watch again over them, as after a new attempt; a
    snapshot or a watch that fails is reported on standard error, and the watching goes on."""

    def __init__(
        self, notifications: Notifications, watcher: FolderWatcher, snapshot: TakeSnapshot
    ) -> None:
        self._notifications = notifications
        self._watcher = watcher
        self._snapshot = snapshot

    async def run(self) -> None:
        """Until the notifications stop."""
        state = await self._first()
        while state is not None and not self._notifications.stopped.is_set():
            state = await self._watch(state)

    async def _first(self) -> WorkspaceSnapshot | None:
        while not self._notifications.stopped.is_set():
            try:
                return await self._snapshot(None)
            except Exception as error:  # the server goes on without notifications for a while
                _warn(f"cannot read the workspace for notifications: {error}")
                await self._pause()
        return None

    async def _watch(self, state: WorkspaceSnapshot) -> WorkspaceSnapshot:
        folders = state.folders
        changes = self._watcher.folder_changes(state.root, folders, self._notifications.stopped)
        try:
            async with aclosing(changes):
                async for _ in changes:
                    state = await self._next(state)
                    if state.folders != folders:
                        break
        except OSError as error:
            _warn(f"the watch of the workspace stopped: {error}; it starts again")
            await self._pause()
            state = await self._next(state)
        return state

    async def _next(self, state: WorkspaceSnapshot) -> WorkspaceSnapshot:
        try:
            after = await self._snapshot(state)
        except Exception as error:  # a failed read must not end the notifications
            _warn(f"cannot read the workspace for notifications: {error}")
            return state
        for change in workspace_changes(state, after):
            self._notifications.notice(change)
        return after

    async def _pause(self) -> None:
        """Waits a while, or until the notifications stop."""
        with suppress(TimeoutError):
            await asyncio.wait_for(
                self._notifications.stopped.wait(), self._notifications.timing.retry_s
            )


def _warn(text: str) -> None:
    print(f"cstudy serve: {text}", file=sys.stderr)
