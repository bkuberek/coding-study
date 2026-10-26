"""Bench-mode measurements across runner restarts (docs/specs/runners.md#bench-mode).

`SubprocessRunner.bench` feeds this the events of each runner process. A hang or crash is
charged to the target and size of the latest `bench_start`: a hang counts as a call over the
budget, a crash as a failure; either way that target stops. The runner then restarts at that size
with the targets still running, which are measured afresh there.
"""

from dataclasses import dataclass, field, replace

from coding_study.adapters.runner_protocol import (
    BenchBudgetExceeded,
    BenchError,
    BenchMemory,
    BenchOutputEvent,
    BenchSampleEvent,
    BenchStart,
    Bye,
    Hello,
    JobEnd,
    JobStart,
    JsonObject,
    LoadError,
    RunnerEvent,
    accepted_hello,
    encode_bench_request,
)
from coding_study.domain.bench_runs import (
    BenchFailure,
    BenchJob,
    BenchOutput,
    BenchReport,
    BenchRequest,
    BenchSample,
    MemoryMeasurement,
    SizeMeasurements,
    TargetReport,
)
from coding_study.domain.errors import RunnerProtocolError
from coding_study.domain.runs import Crashed, RunnerInfo, TimedOut, UserError

NANOSECONDS_PER_MILLISECOND = 1_000_000


@dataclass(slots=True)
class _Measured:
    samples: list[BenchSample] = field(default_factory=list[BenchSample])
    memory: MemoryMeasurement | None = None
    output: BenchOutput | None = None
    exceeded_ns: int | None = None
    failure: BenchFailure | None = None

    def frozen(self, size: int) -> SizeMeasurements:
        return SizeMeasurements(
            size, tuple(self.samples), self.memory, self.output, self.exceeded_ns, self.failure
        )


@dataclass(slots=True)
class _TargetProgress:
    sizes: dict[int, _Measured] = field(default_factory=dict[int, _Measured])
    load_error: UserError | None = None
    stopped: bool = False

    def at(self, size: int) -> _Measured:
        return self.sizes.setdefault(size, _Measured())


class BenchProgress:
    """The `_Progress` of a bench run in `SubprocessRunner`."""

    def __init__(self, request: BenchRequest) -> None:
        self._job: BenchJob = request.job
        self._targets = {target.target_id: _TargetProgress() for target in self._job.targets}
        self._next_size = self._job.inputs[0].size if self._job.inputs else 0
        self._sizes: frozenset[int] = frozenset()
        self._runner: RunnerInfo | None = None
        self._said_hello = False
        self._in_progress: tuple[str, int] | None = None
        self._finished = False
        self._notes: list[str] = []

    @property
    def said_hello(self) -> bool:
        return self._said_hello

    @property
    def call_limit_ms(self) -> int | None:
        return self._job.hang_guard_ms if self._in_progress is not None else None

    @property
    def restart_requested(self) -> bool:
        """Bench mode never runs stress cases, so a runner never asks to be restarted."""
        return False

    def begin_attempt(self) -> JsonObject:
        """The targets still running, from the size where the previous attempt stopped."""
        running = [t for t in self._job.targets if not self._targets[t.target_id].stopped]
        inputs = [i for i in self._job.inputs if i.size >= self._next_size]
        for target in running:
            progress = self._targets[target.target_id]
            for size in [size for size in progress.sizes if size >= self._next_size]:
                del progress.sizes[size]
        self._sizes = frozenset(bench_input.size for bench_input in inputs)
        self._said_hello = False
        self._in_progress = None
        job = replace(self._job, targets=tuple(running), inputs=tuple(inputs))
        return encode_bench_request(BenchRequest(job))

    def apply(self, event: RunnerEvent) -> None:
        if isinstance(event, Hello):
            self._runner = self._runner or accepted_hello(event, self._said_hello)
            self._said_hello = True
            return
        if not self._said_hello:
            raise RunnerProtocolError(f"runner sent {type(event).__name__} before hello")
        match event:
            case JobStart(job_id) | JobEnd(job_id):
                self._require_job(job_id)
                self._in_progress = None
            case Bye():
                self._finished = True
                self._in_progress = None
            case LoadError(job_id, error, target_id):
                self._load_error(job_id, error, target_id)
            case BenchStart(job_id, target_id, size):
                self._measured(job_id, target_id, size)
                self._in_progress = (target_id, size)
            case BenchOutputEvent(job_id, target_id, size, output):
                self._measured(job_id, target_id, size).output = BenchOutput(output)
            case BenchSampleEvent(job_id, target_id, size, sample):
                self._measured(job_id, target_id, size).samples.append(sample)
            case BenchMemory(job_id, target_id, size, memory):
                self._measured(job_id, target_id, size).memory = memory
            case BenchError(job_id, target_id, size, outcome):
                self._measured(job_id, target_id, size).failure = outcome
                self._targets[target_id].stopped = True
            case BenchBudgetExceeded(job_id, target_id, size, wall_ns):
                self._measured(job_id, target_id, size).exceeded_ns = wall_ns
                self._targets[target_id].stopped = True
            case _:
                raise RunnerProtocolError(f"runner sent {type(event).__name__} in bench mode")

    def interrupt(self, outcome: Crashed | TimedOut) -> None:
        culprit = self._in_progress or self._first_running()
        self._in_progress = None
        if culprit is None:
            return
        target_id, size = culprit
        measured = self._targets[target_id].at(size)
        if isinstance(outcome, TimedOut):
            measured.exceeded_ns = outcome.limit_ms * NANOSECONDS_PER_MILLISECOND
            self.note(f"{target_id} ran over {outcome.limit_ms} ms at n={size}")
        else:
            measured.failure = outcome
            self.note(
                f"the runner crashed (exit code {outcome.exit_code}) on {target_id} at n={size}"
            )
        self._targets[target_id].stopped = True
        self._next_size = size

    def is_complete(self) -> bool:
        return self._finished or all(progress.stopped for progress in self._targets.values())

    def note(self, line: str) -> None:
        self._notes.append(line)

    def report(self) -> BenchReport:
        if self._runner is None:
            raise RunnerProtocolError("runner never said hello")
        targets = tuple(
            TargetReport(
                target_id,
                tuple(progress.sizes[size].frozen(size) for size in sorted(progress.sizes)),
                progress.load_error,
            )
            for target_id, progress in self._targets.items()
        )
        return BenchReport(self._runner, targets, tuple(self._notes))

    def _first_running(self) -> tuple[str, int] | None:
        running = (target_id for target_id, p in self._targets.items() if not p.stopped)
        target_id = next(running, None)
        return (target_id, self._next_size) if target_id is not None else None

    def _load_error(self, job_id: str, error: UserError, target_id: str | None) -> None:
        self._require_job(job_id)
        if target_id is None or target_id not in self._targets:
            raise RunnerProtocolError(f'bench load_error for unknown target "{target_id}"')
        self._targets[target_id].load_error = error
        self._targets[target_id].stopped = True

    def _measured(self, job_id: str, target_id: str, size: int) -> _Measured:
        self._require_job(job_id)
        progress = self._targets.get(target_id)
        if progress is None or progress.stopped or size not in self._sizes:
            raise RunnerProtocolError(f'unexpected bench event for "{target_id}" at n={size}')
        return progress.at(size)

    def _require_job(self, job_id: str) -> None:
        if job_id != self._job.job_id:
            raise RunnerProtocolError(f'unknown job "{job_id}"')
