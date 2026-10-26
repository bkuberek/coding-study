"""One stress run of a concurrent job (docs/specs/runners.md#run-procedure).

Every run is independent: fresh argument decoding, a fresh instance, fresh probe sections and
fresh PRNGs. Setup runs on the case thread; the workers wait at a start gate and are released
together; the coordinator waits until every worker finished, one failed, or the deadline passed;
then the final sequence runs. In the threads model a failed or stalled run leaves its workers
behind (Python cannot stop a thread): they are asked to stop between ops, and the caller asks
for a restart when any is still alive shortly after.
"""

import asyncio
import inspect
import random
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from cs_runner.calls import BoundCall, bind
from cs_runner.capture import capture_output
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.events import (
    CaseOutcome,
    FailedAt,
    InvalidOutput,
    Raised,
    Stalled,
    StressFailed,
    StressReturned,
    WorkerProgress,
)
from cs_runner.failures import UserError, describe
from cs_runner.harness import HarnessError, Sections, WorkerHarness
from cs_runner.jobs import arguments_by_name, member_of
from cs_runner.json_value import Json
from cs_runner.perturbation import sleep_yields, thread_perturbation, worker_thread, yield_count
from cs_runner.request import ConcurrentJob, Model, Script, StressCase

HARNESS_PREFIX = "@"
PRNG_MULTIPLIER = 1_000_003
WORKER_STACK_BYTES = 16 * 1024 * 1024
LEFTOVER_GRACE_SECONDS = 0.2
NANOSECONDS_PER_SECOND = 1_000_000_000
SETUP, WORKER, FINAL = "setup", "worker", "final"


def worker_rng(seed: int, ordinal: int) -> random.Random:
    return random.Random(seed * PRNG_MULTIPLIER + ordinal)


@dataclass(frozen=True, slots=True)
class _Op:
    """One op with its arguments decoded: a method call, or a harness op (`call` None)."""

    op: str
    args: tuple[Json, ...]
    symbol: str = ""
    call: BoundCall | None = None


class _OpFailedError(Exception):
    """A failed op, with where it happened."""

    def __init__(self, outcome: Raised | InvalidOutput, at: FailedAt) -> None:
        super().__init__(at.phase)
        self.outcome = outcome
        self.at = at


@dataclass(frozen=True, slots=True)
class StressResult:
    outcome: CaseOutcome
    threads: tuple[threading.Thread, ...] = ()
    """Threads model: the worker threads, which may outlive a failed or stalled run."""

    def leftover_threads(self) -> int:
        """Worker threads still alive after a short grace period."""
        deadline = time.monotonic() + LEFTOVER_GRACE_SECONDS
        for thread in self.threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        return sum(1 for thread in self.threads if thread.is_alive())


def run_stress(design: type, job: ConcurrentJob, case: StressCase) -> StressResult:
    with capture_output() as output:
        result = _run(design, job, case)
    if isinstance(result.outcome, StressReturned | Stalled | StressFailed):
        outcome = _with_stdout(result.outcome, output.text())
        return StressResult(outcome, result.threads)
    return result


def _run(design: type, job: ConcurrentJob, case: StressCase) -> StressResult:
    try:
        plan = _Plan(job, case)
    except _OpFailedError as failure:
        return StressResult(StressFailed(failure.outcome, failure.at))
    if job.model is Model.ASYNC:
        return StressResult(asyncio.run(_AsyncRun(design, job, case, plan).run()))
    return _ThreadRun(design, job, case, plan).run()


class _Plan:
    """Step 1: every argument of setup, workers and final decoded before anything runs."""

    def __init__(self, job: ConcurrentJob, case: StressCase) -> None:
        self.setup = self._ops(job, case.setup, SETUP, None, with_constructor=True)
        self.workers = [
            self._ops(job, script, WORKER, ordinal, with_constructor=False)
            for ordinal, script in enumerate(case.workers)
        ]
        self.final = (
            self._ops(job, case.final, FINAL, None, with_constructor=False) if case.final else []
        )

    def _ops(
        self,
        job: ConcurrentJob,
        script: Script,
        phase: str,
        worker: int | None,
        *,
        with_constructor: bool,
    ) -> list[_Op]:
        ops: list[_Op] = []
        first = 0 if with_constructor else 1
        for index, (op, args) in enumerate(zip(script.ops, script.args, strict=True)):
            if op.startswith(HARNESS_PREFIX):
                ops.append(_Op(op, args))
                continue
            try:
                member = member_of(job.as_class_job(), index + first, op)
                call = bind(member, arguments_by_name(member, args))
            except CaseInputError as error:
                failure = Raised(UserError(type(error).__name__, str(error)), 0)
                raise _OpFailedError(failure, FailedAt(phase, index, worker)) from None
            ops.append(_Op(op, args, member.symbol, call))
        return ops


@dataclass(slots=True)
class _Progress:
    completed: list[int]
    in_op: list[bool]
    finished: list[bool]

    @classmethod
    def of(cls, workers: int) -> "_Progress":
        return cls([0] * workers, [False] * workers, [False] * workers)

    def unfinished(self) -> tuple[WorkerProgress, ...]:
        return tuple(
            WorkerProgress(worker, self.completed[worker], self.in_op[worker])
            for worker in range(len(self.completed))
            if not self.finished[worker]
        )


@dataclass(slots=True)
class _Shared:
    """What workers report to the coordinator."""

    progress: _Progress
    outputs: list[list[Json]]
    sections: Sections = field(default_factory=Sections)
    condition: threading.Condition = field(default_factory=threading.Condition)
    failure: _OpFailedError | None = None
    stopped: bool = False

    def fail(self, failure: _OpFailedError) -> None:
        with self.condition:
            if self.failure is None:
                self.failure = failure
            self.condition.notify_all()

    def finish(self, worker: int) -> None:
        with self.condition:
            self.progress.finished[worker] = True
            self.condition.notify_all()

    def all_finished(self) -> bool:
        return all(self.progress.finished)


class _Base:
    def __init__(self, design: type, job: ConcurrentJob, case: StressCase, plan: _Plan) -> None:
        self._design = design
        self._job = job
        self._case = case
        self._plan = plan
        self._instance: object = None
        workers = len(plan.workers)
        self._shared = _Shared(_Progress.of(workers), [[None] * len(ops) for ops in plan.workers])

    def _failed(self, error: BaseException, at: FailedAt, duration_ns: int) -> _OpFailedError:
        if isinstance(error, InvalidOutputError):
            return _OpFailedError(InvalidOutput(error.reason, duration_ns), at)
        if isinstance(error, HarnessError):
            return _OpFailedError(Raised(UserError("HarnessError", str(error)), duration_ns), at)
        return _OpFailedError(Raised(describe(error, self._job.path), duration_ns), at)

    def _phase_failure(self, error: BaseException, phase: str, index: int) -> _OpFailedError:
        return self._failed(error, FailedAt(phase, index), 0)

    def _worker_failure(self, error: BaseException, ordinal: int, index: int) -> _OpFailedError:
        return self._failed(error, FailedAt(WORKER, index, ordinal), 0)

    def _encode(self, op: _Op, value: object) -> Json:
        assert op.call is not None
        return op.call.encode_result(value)

    def _method(self, op: _Op) -> Callable[..., object]:
        return getattr(self._instance, op.symbol)

    def _ended(self, started_ns: int, ended_ns: int) -> CaseOutcome | None:
        """The outcome of a failed or stalled run; None when every worker finished."""
        shared = self._shared
        duration_ns = ended_ns - started_ns
        failure = shared.failure
        if failure is not None:
            at = FailedAt(
                failure.at.phase,
                failure.at.op_index,
                failure.at.worker,
                shared.progress.unfinished(),
            )
            outcome = _with_duration(failure.outcome, duration_ns)
            return StressFailed(outcome, at)
        if not shared.all_finished():
            return Stalled(shared.progress.unfinished(), duration_ns)
        return None

    def _returned(self, setup: list[Json], final: list[Json], duration_ns: int) -> CaseOutcome:
        shared = self._shared
        return StressReturned(setup, shared.outputs, final, shared.sections.snapshot(), duration_ns)


class _ThreadRun(_Base):
    def run(self) -> StressResult:
        try:
            setup = self._sequence(self._plan.setup, SETUP, with_constructor=True)
        except _OpFailedError as failure:
            return StressResult(StressFailed(failure.outcome, failure.at))
        workers = len(self._plan.workers)
        gate = threading.Barrier(workers + 1)
        threads = self._threads(gate)
        with thread_perturbation(self._case.perturb, self._job.path):
            for thread in threads:
                thread.start()
            gate.wait()
            started_ns = time.perf_counter_ns()
            self._wait_for_workers()
            ended_ns = time.perf_counter_ns()
            self._shared.stopped = True
        ended = self._ended(started_ns, ended_ns)
        if ended is not None:
            return StressResult(ended, tuple(threads))
        try:
            final = self._sequence(self._plan.final, FINAL, with_constructor=False)
        except _OpFailedError as failure:
            return StressResult(StressFailed(failure.outcome, failure.at), tuple(threads))
        return StressResult(self._returned(setup, final, ended_ns - started_ns), tuple(threads))

    def _sequence(self, ops: Sequence[_Op], phase: str, *, with_constructor: bool) -> list[Json]:
        outputs: list[Json] = []
        for index, op in enumerate(ops):
            try:
                if with_constructor and index == 0:
                    assert op.call is not None
                    self._instance = self._design(*op.call.arguments)
                    outputs.append(None)
                    continue
                outputs.append(self._sequential_op(op))
            except (Exception, SystemExit) as error:
                raise self._phase_failure(error, phase, index) from None
        return outputs

    def _sequential_op(self, op: _Op) -> Json:
        if op.call is None:
            WorkerHarness(self._shared.sections, sleep_yields).run(op.op, op.args)
            return None
        assert op.call is not None
        return self._encode(op, self._method(op)(*op.call.arguments))

    def _threads(self, gate: threading.Barrier) -> list[threading.Thread]:
        previous = threading.stack_size(WORKER_STACK_BYTES)
        try:
            return [
                threading.Thread(
                    target=self._work,
                    args=(ordinal, gate),
                    name=f"cs-worker-{ordinal}",
                    daemon=True,
                )
                for ordinal in range(len(self._plan.workers))
            ]
        finally:
            threading.stack_size(previous)

    def _wait_for_workers(self) -> None:
        """Until every worker finished, one failed, or the deadline passed since the gate."""
        shared = self._shared
        timeout = self._case.deadline_ns / NANOSECONDS_PER_SECOND
        with shared.condition:
            shared.condition.wait_for(
                lambda: shared.failure is not None or shared.all_finished(), timeout
            )

    def _work(self, ordinal: int, gate: threading.Barrier) -> None:
        shared = self._shared
        perturb = self._case.perturb
        rng = worker_rng(self._case.seed, ordinal)
        harness = WorkerHarness(shared.sections, sleep_yields)
        progress = shared.progress
        outputs = shared.outputs[ordinal]
        with worker_thread(rng, perturb):
            gate.wait()
            for index, op in enumerate(self._plan.workers[ordinal]):
                if shared.stopped:
                    return
                sleep_yields(yield_count(rng, perturb))
                progress.in_op[ordinal] = True
                try:
                    if op.call is None:
                        harness.run(op.op, op.args)
                    else:
                        outputs[index] = self._encode(op, self._method(op)(*op.call.arguments))
                except (Exception, SystemExit) as error:
                    shared.fail(self._worker_failure(error, ordinal, index))
                    return
                progress.completed[ordinal] = index + 1
                progress.in_op[ordinal] = False
        shared.finish(ordinal)


class _WorkerFailedError(Exception):
    """Ends a failed async worker's task, so `asyncio.wait` returns at once."""


class _AsyncRun(_Base):
    async def run(self) -> CaseOutcome:
        try:
            setup = await self._sequence(self._plan.setup, SETUP, with_constructor=True)
        except _OpFailedError as failure:
            return StressFailed(failure.outcome, failure.at)
        gate = asyncio.Event()
        tasks = [
            asyncio.create_task(self._work(ordinal, gate))
            for ordinal in range(len(self._plan.workers))
        ]
        gate.set()
        started_ns = time.perf_counter_ns()
        timeout = self._case.deadline_ns / NANOSECONDS_PER_SECOND
        _, pending = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_EXCEPTION)
        ended_ns = time.perf_counter_ns()
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.wait(pending, timeout=LEFTOVER_GRACE_SECONDS)
        for task in tasks:
            if task.done() and not task.cancelled():
                task.exception()
        ended = self._ended(started_ns, ended_ns)
        if ended is not None:
            return ended
        try:
            final = await self._sequence(self._plan.final, FINAL, with_constructor=False)
        except _OpFailedError as failure:
            return StressFailed(failure.outcome, failure.at)
        return self._returned(setup, final, ended_ns - started_ns)

    async def _sequence(
        self, ops: Sequence[_Op], phase: str, *, with_constructor: bool
    ) -> list[Json]:
        outputs: list[Json] = []
        harness = WorkerHarness(self._shared.sections, _no_pause)
        for index, op in enumerate(ops):
            try:
                if with_constructor and index == 0:
                    assert op.call is not None
                    self._instance = self._design(*op.call.arguments)
                    outputs.append(None)
                elif op.call is None:
                    harness.run(op.op, op.args)
                    outputs.append(None)
                else:
                    outputs.append(await self._call(op))
            except (Exception, SystemExit) as error:
                raise self._phase_failure(error, phase, index) from None
        return outputs

    async def _call(self, op: _Op) -> Json:
        assert op.call is not None
        value = self._method(op)(*op.call.arguments)
        if inspect.isawaitable(value):
            value = await value
        return self._encode(op, value)

    async def _work(self, ordinal: int, gate: asyncio.Event) -> None:
        shared = self._shared
        perturb = self._case.perturb
        rng = worker_rng(self._case.seed, ordinal)
        pauses: list[int] = []
        harness = WorkerHarness(shared.sections, pauses.append)
        progress = shared.progress
        outputs = shared.outputs[ordinal]
        await gate.wait()
        for index, op in enumerate(self._plan.workers[ordinal]):
            await _yield_to_loop(yield_count(rng, perturb))
            progress.in_op[ordinal] = True
            try:
                if op.call is None:
                    harness.run(op.op, op.args)
                    await _yield_to_loop(sum(pauses))
                    pauses.clear()
                else:
                    outputs[index] = await self._call(op)
            except (Exception, SystemExit) as error:
                shared.fail(self._worker_failure(error, ordinal, index))
                raise _WorkerFailedError from None
            progress.completed[ordinal] = index + 1
            progress.in_op[ordinal] = False
        shared.finish(ordinal)


async def _yield_to_loop(count: int) -> None:
    for _ in range(count):
        await asyncio.sleep(0)


def _no_pause(count: int) -> None:
    """Setup and final run alone, so `@pause` there has nobody to yield to."""
    del count


def _with_duration(outcome: Raised | InvalidOutput, duration_ns: int) -> Raised | InvalidOutput:
    if isinstance(outcome, Raised):
        return Raised(outcome.error, duration_ns, outcome.stdout)
    return InvalidOutput(outcome.reason, duration_ns, outcome.stdout)


def _with_stdout(
    outcome: StressReturned | Stalled | StressFailed, stdout: str
) -> StressReturned | Stalled | StressFailed:
    match outcome:
        case StressReturned():
            return StressReturned(
                outcome.setup,
                outcome.workers,
                outcome.final,
                outcome.sections,
                outcome.duration_ns,
                stdout,
            )
        case Stalled():
            return Stalled(outcome.progress, outcome.duration_ns, stdout)
        case StressFailed(failure=failure, at=at):
            if isinstance(failure, Raised):
                return StressFailed(Raised(failure.error, failure.duration_ns, stdout), at)
            return StressFailed(InvalidOutput(failure.reason, failure.duration_ns, stdout), at)
