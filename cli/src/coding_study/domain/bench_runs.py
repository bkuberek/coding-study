"""What `cstudy bench` asks a runner to measure and what came back
(docs/specs/runners.md#bench-mode).

A bench request holds one job: every target (the user's code and the references) runs in one
process on the same inputs, one input per size. Like test requests it never carries expected
values; the runner only measures.
"""

from dataclasses import dataclass

from coding_study.domain.cases import JsonValue
from coding_study.domain.naming import SymbolNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import (
    Crashed,
    InvalidOutput,
    Raised,
    RunInput,
    RunnerInfo,
    RunTarget,
    UserError,
)
from coding_study.domain.signature import Signature

USER_TARGET_ID = "user"
"""The user's code; references use their approach id."""


@dataclass(frozen=True, slots=True)
class BenchTarget:
    target_id: str
    target: RunTarget
    names: SymbolNames
    emits_output: bool = False
    """Report the output of each size's check call, so the CLI can judge it."""


@dataclass(frozen=True, slots=True)
class BenchInput:
    size: int
    input: RunInput
    max_batch: int
    """At most this many calls per timed sample, each on its own copy of the input."""


@dataclass(frozen=True, slots=True)
class Warmup:
    """Warm up until the coefficient of variation of the latest runs is at most `cv`."""

    min_runs: int
    max_runs: int
    cv: float


@dataclass(frozen=True, slots=True)
class BenchSettings:
    reps: int
    warmup: Warmup
    budget_ms: int
    memory: bool
    min_sample_ns: int


@dataclass(frozen=True, slots=True)
class BenchJob:
    job_id: str
    kind: ProblemKind
    signature: Signature
    targets: tuple[BenchTarget, ...]
    inputs: tuple[BenchInput, ...]
    """Ascending sizes."""
    settings: BenchSettings
    hang_guard_ms: int
    """How long one call (or batch of calls) may run; enforced CLI-side, never sent."""

    def __post_init__(self) -> None:
        identifiers = [target.target_id for target in self.targets]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError(f"duplicate target id in bench job {self.job_id}")
        sizes = [bench_input.size for bench_input in self.inputs]
        if sizes != sorted(set(sizes)):
            raise ValueError(f"bench job {self.job_id} needs distinct ascending sizes")


@dataclass(frozen=True, slots=True)
class BenchRequest:
    """A `bench` mode request; the protocol allows several jobs, `cstudy bench` sends one."""

    job: BenchJob


@dataclass(frozen=True, slots=True)
class BenchSample:
    rep: int
    wall_ns: int
    cpu_ns: int
    calls: int
    """Back-to-back calls the sample timed; times per call are these divided by `calls`."""

    @property
    def per_call_ns(self) -> float:
        return self.wall_ns / self.calls

    @property
    def cpu_per_call_ns(self) -> float:
        return self.cpu_ns / self.calls


@dataclass(frozen=True, slots=True)
class MemoryMeasurement:
    metric: str
    """`tracemalloc_peak`, `heap_used_delta` or `thread_allocated_bytes`."""
    bytes: int


@dataclass(frozen=True, slots=True)
class BenchOutput:
    """What the check call returned; wrapped because `null` is a legitimate output."""

    value: JsonValue


type BenchFailure = Raised | InvalidOutput | Crashed


@dataclass(frozen=True, slots=True)
class SizeMeasurements:
    """Everything one target reported at one size."""

    size: int
    samples: tuple[BenchSample, ...] = ()
    memory: MemoryMeasurement | None = None
    output: BenchOutput | None = None
    exceeded_ns: int | None = None
    """A single call took this long, over the budget or the hang guard; the target stopped."""
    failure: BenchFailure | None = None
    """The target failed here and stopped."""


@dataclass(frozen=True, slots=True)
class TargetReport:
    target_id: str
    sizes: tuple[SizeMeasurements, ...] = ()
    """The sizes the target reached, ascending."""
    load_error: UserError | None = None

    def at(self, size: int) -> SizeMeasurements | None:
        return next((measured for measured in self.sizes if measured.size == size), None)


@dataclass(frozen=True, slots=True)
class BenchReport:
    runner: RunnerInfo
    targets: tuple[TargetReport, ...] = ()
    notes: tuple[str, ...] = ()
    """Hangs, crashes and restarts the CLI recovered from."""

    def target(self, target_id: str) -> TargetReport:
        return next(report for report in self.targets if report.target_id == target_id)
