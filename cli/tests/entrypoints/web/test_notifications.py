"""The notification stream (docs/specs/web-ui.md#notifications): notices reach every live stream,
numbered, a stream that comes back gets what it missed, progress changes are spaced out, runs and
jobs announce their start and end, a watch of the workspace turns changes on disk into notices, and
every stream ends when the server stops. Streams are read as the async generators they are, since
Starlette's test client would wait for the end of the response."""

import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Iterator, Sequence
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from coding_study.application.attempt_changes import (
    WatchedFolder,
    WorkspaceSnapshot,
    workspace_snapshot,
)
from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.notifications import (
    ChildNotices,
    Notifications,
    NotificationTiming,
    WorkspaceWatch,
)
from coding_study.entrypoints.web.runs import Child, Children, ChildStart
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.scripted_runs import QUICK, RUN_END, RUN_START, Script, eventually, outs
from tests.waits import GENEROUS_WAIT_S
from tests.web_server import WRITE_HEADERS, anonymous_client, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
JAVA_PACKAGE = "jvm/java/src/main/java/practice/two_sum"
TIMEOUT_S = GENEROUS_WAIT_S
QUIET_S = 0.3
SPACED = NotificationTiming(keep_alive_s=30, progress_interval_s=0.2, retry_s=0.05)
EVENTS = "/api/v1/events"
ENDED = "ended"
FILE_CHANGED = {"attempt_id": 3, "path": "bank/bank.py", "sha256": "ab"}


async def next_frame(frames: AsyncIterator[str]) -> str:
    return await asyncio.wait_for(anext(frames), TIMEOUT_S)


async def quiet(frames: AsyncIterator[str]) -> bool:
    """Whether the stream says nothing for a while."""
    try:
        await asyncio.wait_for(anext(frames), QUIET_S)
    except TimeoutError:
        return True
    return False


def event_of(frame: str) -> tuple[str, dict[str, object]]:
    lines = dict(line.split(": ", 1) for line in frame.strip().splitlines())
    return lines["event"], json.loads(lines["data"])


def ids_of(body: str) -> list[int]:
    return [int(line[4:]) for line in body.splitlines() if line.startswith("id: ")]


# the stream


def test_a_notice_reaches_a_live_stream():
    async def first() -> str:
        notifications = Notifications(SPACED)
        frames = notifications.frames(None)
        waiting = asyncio.ensure_future(next_frame(frames))
        await asyncio.sleep(0)
        notifications.publish("file_changed", FILE_CHANGED)
        return await waiting

    data = json.dumps(FILE_CHANGED)
    assert asyncio.run(first()) == f"id: 0\nevent: file_changed\ndata: {data}\n\n"


def test_a_new_stream_starts_with_the_notices_after_it_opened():
    async def first_id() -> int:
        notifications = Notifications(SPACED)
        notifications.publish("progress_changed", {})
        frames = notifications.frames(None)
        waiting = asyncio.ensure_future(next_frame(frames))
        await asyncio.sleep(0)
        notifications.publish("file_changed", FILE_CHANGED)
        return ids_of(await waiting)[0]

    assert asyncio.run(first_id()) == 1


async def replayed(published: int, last_event_id: int) -> list[int]:
    """The ids a stream that comes back after `last_event_id` gets, of `published` notices."""
    notifications = Notifications(SPACED)
    for _ in range(published):
        notifications.publish("progress_changed", {})
    notifications.stop()
    frames = [frame async for frame in notifications.frames(last_event_id)]
    return [number for frame in frames for number in ids_of(frame)]


def test_a_stream_that_comes_back_gets_the_notices_after_its_last_id():
    assert asyncio.run(replayed(4, 1)) == [2, 3]


def test_only_the_last_100_notices_are_kept_for_a_stream_that_comes_back():
    assert asyncio.run(replayed(105, 0)) == list(range(5, 105))


def test_a_silent_stream_gets_a_keep_alive_comment():
    async def first() -> str:
        notifications = Notifications(NotificationTiming(keep_alive_s=0.05))
        return await next_frame(notifications.frames(None))

    assert asyncio.run(first()) == ": keep-alive\n\n"


def test_stopping_ends_every_live_stream():
    async def ended() -> list[str]:
        notifications = Notifications(SPACED)
        frames = notifications.frames(None)
        waiting = asyncio.ensure_future(next_frame(frames))
        await asyncio.sleep(0)
        notifications.stop()
        try:
            await waiting
        except StopAsyncIteration:
            return []
        return ["a frame"]

    assert asyncio.run(ended()) == []


def test_a_progress_change_within_the_interval_comes_once_it_ends():
    async def sent() -> list[str]:
        notifications = Notifications(SPACED)
        frames = notifications.frames(None)
        for _ in range(3):
            notifications.progress_changed()
            await asyncio.sleep(0.01)
        first, second = await next_frame(frames), await next_frame(frames)
        return [event_of(first)[0], event_of(second)[0], str(await quiet(frames))]

    assert asyncio.run(sent()) == ["progress_changed", "progress_changed", "True"]


# runs and jobs


def child_start(script: Script, workspace: Path, command: str = "test") -> ChildStart:
    return ChildStart(
        script.child,
        workspace,
        (command, "two-sum", "--lang", "python", "--events"),
        command,
        f"{command} two-sum · python",
        attempt_id=7,
    )


type Launch = Callable[[Children, ChildStart], Awaitable[Child]]


async def lifecycle(tmp_path: Path, launch: Launch, command: str) -> tuple[str, list[object]]:
    """The child's id and the notices its start and end send, with a scripted child."""
    script = Script(tmp_path / "script.json")
    script.play(*outs(RUN_START, RUN_END), {"exit": 0})
    notifications = Notifications(SPACED)
    children = Children(QUICK)
    children.listen(ChildNotices(notifications))
    frames = notifications.frames(None)
    child = await launch(children, child_start(script, tmp_path, command))
    return child.id, [event_of(await next_frame(frames)) for _ in range(2)]


def test_a_run_tells_every_tab_it_started_and_ended(tmp_path):
    run_id, sent = asyncio.run(lifecycle(tmp_path, Children.start_run, "test"))
    run = {"run_id": run_id, "attempt_id": 7, "command": "test"}
    assert sent == [("run_started", run), ("run_ended", {**run, "exit_code": 0})]


def test_a_job_tells_every_tab_it_started_and_ended(tmp_path):
    job_id, sent = asyncio.run(lifecycle(tmp_path, Children.start_job, "verify"))
    job = {"job_id": job_id, "command": "verify"}
    assert sent == [("job_started", job), ("job_ended", {**job, "exit_code": 0})]


def test_stopping_the_runs_and_jobs_ends_the_notification_streams():
    async def ended() -> bool:
        notifications = Notifications(SPACED)
        children = Children(QUICK)
        children.listen(ChildNotices(notifications))
        frames = notifications.frames(None)
        waiting = asyncio.ensure_future(next_frame(frames))
        await asyncio.sleep(0)
        await children.stop()
        try:
            await waiting
        except StopAsyncIteration:
            return True
        return False

    assert asyncio.run(ended())


# the watch of the workspace


class ScriptedWatcher:
    """Yields once per `burst()`, and records the folders of every watch it starts."""

    def __init__(self) -> None:
        self.watches: list[tuple[WatchedFolder, ...]] = []
        self._bursts: asyncio.Queue[None] = asyncio.Queue()
        self._started = asyncio.Event()

    def burst(self) -> None:
        self._bursts.put_nowait(None)

    async def watching(self, count: int = 1) -> None:
        while len(self.watches) < count:
            self._started.clear()
            await asyncio.wait_for(self._started.wait(), TIMEOUT_S)

    async def folder_changes(
        self, root: Path, folders: Sequence[WatchedFolder], stop_event: asyncio.Event
    ) -> AsyncGenerator[None]:
        self.watches.append(tuple(folders))
        self._started.set()
        while not stop_event.is_set():
            burst = asyncio.ensure_future(self._bursts.get())
            stop = asyncio.ensure_future(stop_event.wait())
            await asyncio.wait([burst, stop], return_when=asyncio.FIRST_COMPLETED)
            stop.cancel()
            if not burst.done():
                burst.cancel()
                return
            yield None


@pytest.fixture
def project(tmp_path) -> tuple[Environment, Attempt]:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    return environment, start_attempt(environment, StartRequest(PROJECT_SLUG)).attempt


def snapshots_of(environment: Environment):
    async def take(previous: WorkspaceSnapshot | None) -> WorkspaceSnapshot:
        return workspace_snapshot(environment, previous)

    return take


async def watched(
    environment: Environment, change: Callable[[], None], bursts: int = 1
) -> tuple[list[str], ScriptedWatcher]:
    """The notices that `change`, then `bursts` bursts of events, send."""
    notifications = Notifications(SPACED)
    watcher = ScriptedWatcher()
    watch = asyncio.create_task(
        WorkspaceWatch(notifications, watcher, snapshots_of(environment)).run()
    )
    frames = notifications.frames(None)
    await watcher.watching()
    change()
    for _ in range(bursts):
        watcher.burst()
    sent = [await next_frame(frames)]
    while not await quiet(frames):
        sent.append("more")
    notifications.stop()
    await asyncio.wait_for(watch, TIMEOUT_S)
    return sent, watcher


def test_a_file_saved_on_disk_is_a_file_change(project):
    environment, attempt = project
    bank = environment.workspace.absolute(f"projects/{PROJECT_SLUG}/bank/bank.py")
    sent, _watcher = asyncio.run(watched(environment, lambda: bank.write_text("x\n")))
    sha256 = hashlib.sha256(b"x\n").hexdigest()
    saved = {"attempt_id": attempt.id, "path": "bank/bank.py", "sha256": sha256}
    assert [event_of(frame) for frame in sent] == [("file_changed", saved)]


def test_a_burst_that_changes_nothing_sends_nothing(project):
    environment, _attempt = project

    async def nothing() -> bool:
        notifications = Notifications(SPACED)
        watcher = ScriptedWatcher()
        watch = asyncio.create_task(
            WorkspaceWatch(notifications, watcher, snapshots_of(environment)).run()
        )
        frames = notifications.frames(None)
        await watcher.watching()
        watcher.burst()
        silent = await quiet(frames)
        notifications.stop()
        await asyncio.wait_for(watch, TIMEOUT_S)
        return silent

    assert asyncio.run(nothing())


def test_a_new_attempt_restarts_the_watch_with_its_folder(tmp_path):
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    environment = make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))

    async def second_watch() -> tuple[WatchedFolder, ...]:
        notifications = Notifications(SPACED)
        watcher = ScriptedWatcher()
        watch = asyncio.create_task(
            WorkspaceWatch(notifications, watcher, snapshots_of(environment)).run()
        )
        await watcher.watching()
        start_attempt(environment, StartRequest("two-sum", Language.JAVA))
        watcher.burst()
        await watcher.watching(2)
        notifications.stop()
        await asyncio.wait_for(watch, TIMEOUT_S)
        return watcher.watches[1]

    assert WatchedFolder(JAVA_PACKAGE, False) in asyncio.run(second_watch())


def test_a_snapshot_that_fails_sends_nothing_and_the_watch_goes_on(project):
    environment, _attempt = project
    failures = iter([None, OSError("progress.db is busy")])

    async def take(previous: WorkspaceSnapshot | None) -> WorkspaceSnapshot:
        failure = next(failures, None)
        if failure is not None:
            raise failure
        return workspace_snapshot(environment, previous)

    async def after_failure() -> list[str]:
        notifications = Notifications(SPACED)
        watcher = ScriptedWatcher()
        watch = asyncio.create_task(WorkspaceWatch(notifications, watcher, take).run())
        frames = notifications.frames(None)
        await watcher.watching()
        watcher.burst()
        await asyncio.sleep(0.05)
        environment.workspace.absolute(f"projects/{PROJECT_SLUG}/README.md").unlink()
        watcher.burst()
        frame = await next_frame(frames)
        notifications.stop()
        await asyncio.wait_for(watch, TIMEOUT_S)
        return [event_of(frame)[0]]

    assert asyncio.run(after_failure()) == ["file_changed"]


class FailingOnce(ScriptedWatcher):
    """A watch whose first start fails, as on a folder that went meanwhile."""

    async def folder_changes(
        self, root: Path, folders: Sequence[WatchedFolder], stop_event: asyncio.Event
    ) -> AsyncGenerator[None]:
        if not self.watches:
            self.watches.append(tuple(folders))
            raise RuntimeError("the folder went")
        async for burst in super().folder_changes(root, folders, stop_event):
            yield burst


def test_a_watch_that_fails_starts_again(project):
    environment, _attempt = project

    async def watches() -> int:
        notifications = Notifications(SPACED)
        watcher = FailingOnce()
        watch = asyncio.create_task(
            WorkspaceWatch(notifications, watcher, snapshots_of(environment)).run()
        )
        await watcher.watching(2)
        notifications.stop()
        await asyncio.wait_for(watch, TIMEOUT_S)
        return len(watcher.watches)

    assert asyncio.run(watches()) == 2


# the endpoint


@pytest.fixture
def stopped(tmp_path) -> Iterator[TestClient]:
    """A server that sent four notices and stopped its notifications, so a stream ends."""
    notifications = Notifications(SPACED)

    def four_then_stop() -> None:
        for _ in range(4):
            notifications.publish("progress_changed", {})
        notifications.stop()

    with session_client(web_app(tmp_path, notifications=notifications)) as client:
        assert client.portal is not None, "the client runs the app in a loop of its own"
        client.portal.call(four_then_stop)
        yield client


def test_the_events_are_an_event_stream(stopped):
    assert stopped.get(EVENTS).headers["content-type"].startswith("text/event-stream")


def test_the_events_replay_what_came_after_the_last_event_id(stopped):
    assert ids_of(stopped.get(EVENTS, headers={"Last-Event-ID": "1"}).text) == [2, 3]


def test_the_events_need_the_session(tmp_path):
    with anonymous_client(web_app(tmp_path)) as client:
        assert client.get(EVENTS).status_code == 401


def test_a_run_started_from_the_page_tells_every_tab(tmp_path, project):
    environment, attempt = project
    script = Script(tmp_path / "script.json")
    script.play(*outs(RUN_START, RUN_END), {"exit": 0})
    notifications = Notifications(SPACED)

    async def everything_sent() -> list[str]:
        notifications.stop()
        return [event_of(frame)[0] async for frame in notifications.frames(-1)]

    app = web_app(tmp_path, environment, script.child, Children(QUICK), notifications)
    with session_client(app) as client:
        body = {"attempt_id": attempt.id, "command": "test"}
        run_id = client.post("/api/v1/runs", json=body, headers=WRITE_HEADERS).json()["id"]
        eventually(lambda: client.get(f"/api/v1/runs/{run_id}").json()["state"], ENDED.__eq__)
        assert client.portal is not None, "the client runs the app in a loop of its own"
        assert client.portal.call(everything_sent) == ["run_started", "run_ended"]
