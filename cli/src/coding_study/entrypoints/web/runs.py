"""The runs and jobs of the server (docs/specs/web-ui.md#runs, docs/specs/web-ui.md#jobs).

Each is a child `cstudy` whose output the server relays as server-sent events. A run relays the
`--events` lines of `cstudy test` or `cstudy submit` unchanged; a job relays the lines of a
command's text report. Every message stays in memory, so a stream can start again after any of
them (`Last-Event-ID`), until ten newer runs of the same attempt, or ten newer jobs, take its
place. A slot is held from the start until the child exits, not until its `run_end`: a run asked
for right after a cancel must wait until the child is gone.

Cancel sends SIGINT, as Ctrl-C does in a terminal; a child still alive after a while gets SIGTERM,
and after another while SIGKILL, with everything left in its process group.
"""

import asyncio
import json
import secrets
import signal
import sys
from collections import deque
from collections.abc import AsyncIterator, Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, cast

from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.web.children import ChildCommand, StreamedChild, start_child
from coding_study.entrypoints.web.errors import ApiError, ErrorCode

ID_BYTES = 8
"""Ids of 16 hex digits."""
RETAINED = 10
STDERR_LINES = 20
CLOSED_EVENT = "closed"
LINE_EVENT = "line"
RUN_END = "run_end"
KEEP_ALIVE = ": keep-alive\n\n"
SIGNAL_EXIT_BASE = 128
"""A shell reports a process that a signal ended as 128 + the signal's number."""

type Report = Callable[[str, str], None]
"""Prints a line on the server's standard output: its label (`run`, `job`) and its text."""


def _report_nothing(_label: str, _text: str) -> None:
    pass


class ChildKind(StrEnum):
    RUN = "run"
    JOB = "job"


@dataclass(frozen=True, slots=True)
class ChildTiming:
    terminate_after_s: float = 10.0
    """How long a cancelled child has after SIGINT before it gets SIGTERM."""
    kill_after_s: float = 5.0
    """How long it has after SIGTERM before it gets SIGKILL."""
    keep_alive_s: float = 15.0
    """How long a stream stays silent before a comment line keeps the connection open."""
    drain_s: float = 1.0
    """How long the output of a child that exited is still read, while a process it left behind
    holds its pipes open."""


@dataclass(frozen=True, slots=True)
class ChildStart:
    """What a run or a job starts, and what the server says about it."""

    child: ChildCommand
    workspace: Path
    arguments: tuple[str, ...]
    """The `cstudy` arguments after the global flags: `test two-sum --lang python --events`."""
    command: str
    """As the request named it: `test`, `submit`, `doctor_fix`, `verify`, `bench`."""
    title: str
    """The start of the line the server prints when it ends: `test two-sum · python`."""
    options: Mapping[str, JsonValue] = field(default_factory=dict[str, JsonValue])
    attempt_id: int | None = None
    """A run's attempt, whose slot it takes."""
    excludes_runs: bool = False
    """A job that starts only while no run runs, and while it runs no run starts."""


@dataclass(frozen=True, slots=True)
class Message:
    """A server-sent event: `event` names it, `data` is one line of JSON."""

    event: str
    data: str

    def frame(self, index: int | None = None) -> str:
        head = "" if index is None else f"id: {index}\n"
        return f"{head}event: {self.event}\ndata: {self.data}\n\n"


@dataclass(frozen=True, slots=True)
class Closed:
    """The server's last message on a stream, sent once the child exited."""

    exit_code: int
    signal: str | None
    """The signal that ended the child, such as `SIGKILL`."""
    stderr: tuple[str, ...]
    """The last lines of standard error when no `run_end` came."""

    def message(self) -> Message:
        document = {"exit_code": self.exit_code, "signal": self.signal, "stderr": [*self.stderr]}
        return Message(CLOSED_EVENT, json.dumps(document))


class Relay(Protocol):
    """Makes messages of a child's output lines."""

    def stdout(self, line: str) -> Message | None:
        """None drops the line, which is not what the child should write."""
        ...

    def stderr(self, line: str) -> Message | None:
        """None keeps the line for `closed` only."""
        ...


class EventRelay:
    """A run: each `--events` line, unchanged, its `type` naming the message."""

    def stdout(self, line: str) -> Message | None:
        try:
            event: object = json.loads(line)
        except ValueError:
            return None
        if not isinstance(event, dict):
            return None
        event_type = cast(dict[str, object], event).get("type")
        return Message(event_type, line) if isinstance(event_type, str) else None

    def stderr(self, line: str) -> Message | None:
        return None


class LineRelay:
    """A job: every line of its report, from either stream."""

    def stdout(self, line: str) -> Message | None:
        return _line_message("stdout", line)

    def stderr(self, line: str) -> Message | None:
        return _line_message("stderr", line)


def _line_message(stream: str, text: str) -> Message:
    return Message(LINE_EVENT, json.dumps({"stream": stream, "text": text}))


_RELAYS: Mapping[ChildKind, Relay] = {ChildKind.RUN: EventRelay(), ChildKind.JOB: LineRelay()}


class Child:
    """A run or a job: its process and every message it relayed."""

    def __init__(self, kind: ChildKind, start: ChildStart, timing: ChildTiming) -> None:
        self.id = secrets.token_hex(ID_BYTES)
        self.kind = kind
        self.start = start
        self.started_at = datetime.now(UTC).isoformat(timespec="seconds")
        self.messages: list[Message] = []
        self.run_end: dict[str, Any] | None = None
        self.closed: Closed | None = None
        self._timing = timing
        self._relay = _RELAYS[kind]
        self._stderr: deque[str] = deque(maxlen=STDERR_LINES)
        self._wakeup = asyncio.Event()
        self._ended = asyncio.Event()
        self._process: StreamedChild | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._cancelled = False

    @property
    def running(self) -> bool:
        return self.closed is None

    async def launch(self, ended: Callable[["Child"], None]) -> None:
        """Starts the process; `ended` is called once it exited and its stream closed."""
        process = await start_child(self.start.child, self.start.workspace, self.start.arguments)
        self._process = process
        self._run_task(self._supervise(process, ended))

    def cancel(self) -> None:
        """SIGINT, then SIGTERM and SIGKILL while the child lives on; a second cancel adds
        nothing to the first."""
        if self._cancelled or self._process is None or not self.running:
            return
        self._cancelled = True
        self._run_task(self._escalate(self._process))

    async def wait_ended(self) -> None:
        await self._ended.wait()

    async def frames(self, after: int | None) -> AsyncIterator[str]:
        """The stream: the messages after `after` (all of them for None), the live ones, then
        `closed`; a comment line whenever it would stay silent too long."""
        index = 0 if after is None else after + 1
        while True:
            wakeup = self._wakeup
            while index < len(self.messages):
                yield self.messages[index].frame(index)
                index += 1
            if self.closed is not None:
                yield self.closed.message().frame()
                return
            if not await _within(wakeup.wait(), self._timing.keep_alive_s):
                yield KEEP_ALIVE

    def end_line(self) -> str:
        """What the server prints when the child ended: `test two-sum · python · passed ·
        14/14 · 0.9s`, or the exit code of a child that wrote no `run_end`."""
        assert self.closed is not None
        if self.run_end is None:
            ended = self.closed.signal or f"exit {self.closed.exit_code}"
            return f"{self.start.title} · {ended}"
        return " · ".join((self.start.title, *_run_end_parts(self.run_end)))

    async def _supervise(self, process: StreamedChild, ended: Callable[["Child"], None]) -> None:
        readers = {
            asyncio.create_task(_read_lines(process.stdout, self._take_stdout)),
            asyncio.create_task(_read_lines(process.stderr, self._take_stderr)),
        }
        returncode = await process.exited()
        _, unfinished = await asyncio.wait(readers, timeout=self._timing.drain_s)
        for reader in unfinished:
            reader.cancel()
        await asyncio.gather(*unfinished, return_exceptions=True)
        process.close()
        self.closed = _closed(returncode, () if self.run_end else tuple(self._stderr))
        self._ended.set()
        self._notify()
        ended(self)

    async def _escalate(self, process: StreamedChild) -> None:
        steps = (
            (signal.SIGINT, self._timing.terminate_after_s),
            (signal.SIGTERM, self._timing.kill_after_s),
        )
        for number, grace in steps:
            process.send(number)
            if await _within(process.exited(), grace):
                return
        process.kill_group()

    def _take_stdout(self, line: str) -> None:
        message = self._relay.stdout(line)
        if message is None:
            _warn(f"{self.kind} {self.id}: dropped a line that is not an event: {line}")
            return
        if message.event == RUN_END:
            self.run_end = json.loads(message.data)
        self._append(message)

    def _take_stderr(self, line: str) -> None:
        self._stderr.append(line)
        message = self._relay.stderr(line)
        if message is not None:
            self._append(message)

    def _append(self, message: Message) -> None:
        self.messages.append(message)
        self._notify()

    def _notify(self) -> None:
        """Wakes every stream waiting for a message."""
        self._wakeup.set()
        self._wakeup = asyncio.Event()

    def _run_task(self, work: Coroutine[Any, Any, None]) -> None:
        """Keeps a reference until the task is done, so it is not collected while it runs."""
        task = asyncio.create_task(work)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


class Children:
    """Every run and job of the server, and their slots: one run per attempt, one job at a time,
    and no run while a job that excludes runs runs."""

    def __init__(self, timing: ChildTiming | None = None, report: Report = _report_nothing) -> None:
        self._timing = timing or ChildTiming()
        self._report = report
        self._runs: list[Child] = []
        self._jobs: list[Child] = []
        self._starting = asyncio.Lock()
        self._stopping = False

    async def start_run(self, start: ChildStart) -> Child:
        """Raises ApiError `conflict` while the attempt's slot is taken."""
        async with self._starting:
            self._refuse_new_child()
            exclusive = _first(self._jobs, lambda job: job.running and job.start.excludes_runs)
            if exclusive is not None:
                message = f"cstudy {exclusive.start.title} is running; run when it ends"
                raise ApiError(ErrorCode.CONFLICT, message, {"job": exclusive.id})
            busy = _first(self._runs, lambda run: run.running and _same_attempt(run, start))
            if busy is not None:
                message = f"a run of this attempt is in progress: {busy.start.title}"
                raise ApiError(ErrorCode.CONFLICT, message, {"run": busy.id})
            run = await self._launch(ChildKind.RUN, start)
            self._runs = _retained([*self._runs, run], lambda kept: _same_attempt(kept, start))
            return run

    async def start_job(self, start: ChildStart) -> Child:
        """Raises ApiError `conflict` while a job runs, or, for a job that excludes runs, while
        a run runs."""
        async with self._starting:
            self._refuse_new_child()
            busy = _first(self._jobs, lambda job: job.running)
            if busy is not None:
                message = f"a job is in progress: {busy.start.title}"
                raise ApiError(ErrorCode.CONFLICT, message, {"job": busy.id})
            running = _first(self._runs, lambda run: run.running)
            if start.excludes_runs and running is not None:
                message = f"cstudy {start.title} waits until no run is in progress"
                raise ApiError(ErrorCode.CONFLICT, message, {"run": running.id})
            job = await self._launch(ChildKind.JOB, start)
            self._jobs = _retained([*self._jobs, job], lambda _kept: True)
            return job

    def run(self, run_id: str) -> Child:
        """Raises ApiError `not_found` for an id no retained run has."""
        return _found(self._runs, run_id, ChildKind.RUN)

    def job(self, job_id: str) -> Child:
        """Raises ApiError `not_found` for an id no retained job has."""
        return _found(self._jobs, job_id, ChildKind.JOB)

    def runs_of(self, attempt_id: int) -> list[Child]:
        """The attempt's retained runs, newest first."""
        return [run for run in reversed(self._runs) if run.start.attempt_id == attempt_id]

    async def stop(self) -> None:
        """Cancels every run and job and waits for their children, as the server stops; no new
        one starts from then on."""
        async with self._starting:
            self._stopping = True
        running = [child for child in (*self._runs, *self._jobs) if child.running]
        for child in running:
            child.cancel()
        await asyncio.gather(*(child.wait_ended() for child in running))

    async def _launch(self, kind: ChildKind, start: ChildStart) -> Child:
        child = Child(kind, start, self._timing)
        await child.launch(self._ended)
        return child

    def _ended(self, child: Child) -> None:
        self._report(child.kind, child.end_line())

    def _refuse_new_child(self) -> None:
        if self._stopping:
            raise ApiError(ErrorCode.CONFLICT, "cstudy serve is stopping")


def _same_attempt(run: Child, start: ChildStart) -> bool:
    return run.start.attempt_id == start.attempt_id


def _first(children: list[Child], matches: Callable[[Child], bool]) -> Child | None:
    return next((child for child in children if matches(child)), None)


def _found(children: list[Child], child_id: str, kind: ChildKind) -> Child:
    found = _first(children, lambda child: child.id == child_id)
    if found is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"no {kind} {child_id}")
    return found


def _retained(children: list[Child], same: Callable[[Child], bool]) -> list[Child]:
    """Oldest first, without the ended children of which RETAINED newer ones are `same`."""
    kept: list[Child] = []
    newer = 0
    for child in reversed(children):
        if not same(child):
            kept.append(child)
            continue
        if newer < RETAINED or child.running:
            kept.append(child)
        newer += 1
    return kept[::-1]


def _closed(returncode: int, stderr: tuple[str, ...]) -> Closed:
    if returncode >= 0:
        return Closed(returncode, None, stderr)
    try:
        name = signal.Signals(-returncode).name
    except ValueError:
        name = f"signal {-returncode}"
    return Closed(SIGNAL_EXIT_BASE - returncode, name, stderr)


def _run_end_parts(run_end: dict[str, Any]) -> list[str]:
    """`passed`, `14/14`, `0.9s`: the outcome, then the tally and the time when it has them."""
    parts = [str(run_end.get("outcome"))]
    summary = run_end.get("summary")
    if not isinstance(summary, dict):
        return parts
    document = cast(dict[str, Any], summary)
    tally = document.get("tally")
    if isinstance(tally, dict):
        counts = cast(dict[str, Any], tally)
        parts.append(f"{counts.get('passed')}/{counts.get('total')}")
    duration = document.get("duration_s")
    if isinstance(duration, int | float):
        parts.append(f"{duration:.1f}s")
    return parts


async def _read_lines(stream: asyncio.StreamReader, take: Callable[[str], None]) -> None:
    while True:
        try:
            raw = await stream.readline()
        except ValueError:
            _warn("dropped a line over the length limit")
            continue
        if not raw:
            return
        take(raw.decode(errors="replace").rstrip("\r\n"))


async def _within(waiting: Coroutine[Any, Any, object], seconds: float) -> bool:
    """Whether `waiting` finished within `seconds`; it is cancelled otherwise."""
    try:
        await asyncio.wait_for(waiting, seconds)
    except TimeoutError:
        return False
    return True


def _warn(text: str) -> None:
    print(f"cstudy serve: {text}", file=sys.stderr)
