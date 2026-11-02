"""Grading jobs on the virtual clock (docs/specs/runners.md#virtual-clock-and-stress-in-project-
jobs).

Each case runs on a `VirtualClockLoop` of its own (`cs_support.virtual_clock`), from the
constructor on. The runner makes each operation's call, awaits its result when the result is
awaitable, then settles, so the next operation sees every task waiting. The harness operations
move the clock (`@advance`), start a call as a task without waiting for it (`@spawn`), wait for
that task (`@join`) and read the clock (`@now`).

An operation that waits while no task can run and no timer is due ends the case at once as
`stalled`, naming the operation and the virtual time. Tasks still pending when a case ends are
cancelled, as `asyncio.run` cancels them; threads that a case left running would reach the next
case, so the runner asks for a restart after it. `duration_ns` is the real time of the whole case,
since every clock the code reads is virtual.
"""

import asyncio
import inspect
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace

from cs_runner.calls import BoundCall, bind
from cs_runner.capture import capture_output
from cs_runner.concurrent import RestartRequestError
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.events import (
    ClockOutcome,
    Deadlocked,
    EventWriter,
    InvalidOutput,
    Raised,
    Returned,
)
from cs_runner.failures import UserError, describe
from cs_runner.jobs import (
    CONSTRUCTOR_INDEX,
    arguments_by_name,
    fresh_decimal_context,
    input_error,
    member_of,
)
from cs_runner.json_value import Json, is_int
from cs_runner.loading import TargetLoadError, load_entry_class
from cs_runner.request import Clock, Member, OperationCase, ProjectJob
from cs_support.virtual_clock import DeadlockError, advance, now, run, settle

HARNESS_PREFIX = "@"
ADVANCE, SPAWN, JOIN, NOW = "@advance", "@spawn", "@join", "@now"
LEFTOVER_GRACE_SECONDS = 0.2


def run_clock_job(job: ProjectJob, clock: Clock, events: EventWriter) -> None:
    """Raises RestartRequestError after writing `restart_requested`."""
    events.job_start(job.job_id)
    try:
        design = load_entry_class(job)
    except TargetLoadError as failure:
        events.load_error(job.job_id, failure.error)
        events.job_end(job.job_id)
        return
    for case in job.cases:
        events.case_start(job.job_id, case.case_id)
        threads = frozenset(threading.enumerate())
        outcome = _ClockCase(job, design).run(case, clock.seed)
        events.case_result(job.job_id, case.case_id, outcome)
        left = _threads_left(threads)
        if left:
            events.restart_requested(f"{left} threads of {case.case_id} are still running")
            raise RestartRequestError
    events.job_end(job.job_id)


def _threads_left(before: frozenset[threading.Thread]) -> int:
    """Threads the case started that are still alive after a short grace period."""
    started = [thread for thread in threading.enumerate() if thread not in before]
    deadline = time.monotonic() + LEFTOVER_GRACE_SECONDS
    for thread in started:
        thread.join(max(0.0, deadline - time.monotonic()))
    return sum(1 for thread in started if thread.is_alive())


class _CaseEndedError(Exception):
    """Ends a case early with its outcome: the error of an operation, or its invalid output."""

    def __init__(self, outcome: Raised | InvalidOutput) -> None:
        super().__init__()
        self.outcome = outcome


@dataclass(frozen=True, slots=True)
class _Task:
    """A call that `@spawn` started; `@join` waits for it."""

    call: BoundCall
    future: asyncio.Future[object]


class _ClockCase:
    """One case on the virtual clock: the constructor, then each operation on the new instance."""

    def __init__(self, job: ProjectJob, design: type) -> None:
        self._job = job
        self._design = design
        self._instance: object = None
        self._outputs: list[Json] = []
        self._tasks: dict[str, _Task] = {}
        self._index = CONSTRUCTOR_INDEX
        self._label = ""

    def run(self, case: OperationCase, seed: int) -> ClockOutcome:
        started = time.perf_counter_ns()
        with fresh_decimal_context(), capture_output() as output:
            try:
                outcome = run(self._operations(case), seed=seed)
            except DeadlockError as deadlock:
                outcome = self._deadlocked(deadlock)
        duration_ns = time.perf_counter_ns() - started
        return replace(outcome, duration_ns=duration_ns, stdout=output.text())

    async def _operations(self, case: OperationCase) -> ClockOutcome:
        try:
            for index, (op, args) in enumerate(zip(case.ops, case.args, strict=True)):
                self._enter(index, op, args)
                self._outputs.append(await self._operation(index, op, args))
                await settle()
        except _CaseEndedError as ended:
            return ended.outcome
        return Returned(self._outputs, 0)

    def _enter(self, index: int, op: str, args: Sequence[Json]) -> None:
        """Records the operation in progress, which a deadlock names: a task's name follows
        `@spawn` and `@join`."""
        self._index = index
        named = op in (SPAWN, JOIN) and args and isinstance(args[0], str)
        self._label = f"{op} {args[0]}" if named else op

    async def _operation(self, index: int, op: str, args: Sequence[Json]) -> Json:
        try:
            if index != CONSTRUCTOR_INDEX and op.startswith(HARNESS_PREFIX):
                return await self._harness(op, args)
            member = member_of(self._job, index, op)
            call = bind(member, arguments_by_name(member, args))
        except CaseInputError as error:
            raise self._ended(input_error(error)) from None
        value = await self._awaited(self._invoked(index, member, call))
        if index == CONSTRUCTOR_INDEX:
            self._instance = value
            return None
        return self._encoded(call, value)

    def _invoked(self, index: int, member: Member, call: BoundCall) -> object:
        try:
            if index == CONSTRUCTOR_INDEX:
                return self._design(*call.arguments)
            return getattr(self._instance, member.symbol)(*call.arguments)
        except (Exception, SystemExit) as error:
            raise self._failed(error) from None

    async def _awaited(self, value: object) -> object:
        """The result of an awaitable, else the value; a failure of the awaited code ends the
        case."""
        if not inspect.isawaitable(value):
            return value
        try:
            return await value
        except (Exception, SystemExit) as error:
            raise self._failed(error) from None
        except asyncio.CancelledError as error:
            if _being_cancelled():
                raise
            raise self._failed(error) from None

    def _encoded(self, call: BoundCall, value: object) -> Json:
        try:
            return call.encode_result(value)
        except InvalidOutputError as error:
            reason = f"operation {self._index} ({self._label}): {error.reason}"
            raise _CaseEndedError(InvalidOutput(reason, 0)) from None

    async def _harness(self, op: str, args: Sequence[Json]) -> Json:
        """Raises CaseInputError for an operation or arguments the harness does not know."""
        match op:
            case "@advance":
                await advance(_milliseconds(args))
                return None
            case "@spawn":
                self._spawn(args)
                return None
            case "@join":
                return await self._join(args)
            case "@now":
                if args:
                    raise CaseInputError(f"{NOW} takes no arguments")
                return now()
            case _:
                raise CaseInputError(f'unknown harness operation "{op}" at index {self._index}')

    def _spawn(self, args: Sequence[Json]) -> None:
        match args:
            case [str() as task, str() as method, *arguments]:
                pass
            case _:
                raise CaseInputError(f"{SPAWN} takes a task name, a method and its arguments")
        if task in self._tasks:
            raise CaseInputError(f'task "{task}" was spawned and not joined yet')
        member = self._job.methods.get(method)
        if member is None:
            raise CaseInputError(f'{SPAWN} of an unknown method "{method}"')
        call = bind(member, arguments_by_name(member, arguments))
        value = self._invoked(self._index, member, call)
        self._tasks[task] = _Task(call, _future_of(value))

    async def _join(self, args: Sequence[Json]) -> Json:
        match args:
            case [str() as name]:
                pass
            case _:
                raise CaseInputError(f"{JOIN} takes the name of a spawned task")
        task = self._tasks.pop(name, None)
        if task is None:
            raise CaseInputError(f'{JOIN} of task "{name}", which no {SPAWN} started')
        return self._encoded(task.call, await self._awaited(task.future))

    def _failed(self, error: BaseException) -> _CaseEndedError:
        return self._ended(describe(error, self._job.user_code))

    def _ended(self, error: UserError) -> _CaseEndedError:
        partial = list(self._outputs)
        return _CaseEndedError(Raised(error, 0, op_index=self._index, partial_output=partial))

    def _deadlocked(self, deadlock: DeadlockError) -> Deadlocked:
        reason = f"op {self._index} ({self._label}): deadlock at {deadlock.milliseconds} ms"
        return Deadlocked(reason, self._index, self._outputs[: self._index], 0)


def _milliseconds(args: Sequence[Json]) -> int:
    match args:
        case [milliseconds] if is_int(milliseconds) and milliseconds >= 0:
            return milliseconds
        case _:
            raise CaseInputError(f"{ADVANCE} takes a whole number of milliseconds, 0 or more")


def _future_of(value: object) -> asyncio.Future[object]:
    """The spawned call as a task, or, for a call that returned a plain value, a future that
    holds it."""
    if inspect.isawaitable(value):
        return asyncio.ensure_future(value)
    future: asyncio.Future[object] = asyncio.get_running_loop().create_future()
    future.set_result(value)
    return future


def _being_cancelled() -> bool:
    """Whether the case's own task is being cancelled, as `asyncio.run` does after a deadlock,
    rather than a call it awaits."""
    task = asyncio.current_task()
    return task is not None and task.cancelling() > 0
