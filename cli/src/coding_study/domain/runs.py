"""What the CLI asks a runner to execute and what came back (docs/specs/runners.md).

A request carries inputs only: runners never see expected values. A report holds one outcome per
requested case; judging those outcomes against expected values is core logic, done elsewhere.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.cases import FunctionInput, JsonValue, OperationSequence
from coding_study.domain.concurrency import ConcurrencyModel, Perturbation, ThreadKind
from coding_study.domain.naming import SymbolNames
from coding_study.domain.problem import Language, ProblemKind
from coding_study.domain.signature import Signature

PROTOCOL_VERSION = 1

HELLO_TIMEOUT_MS: Mapping[Language, int] = {
    Language.PYTHON: 5_000,
    Language.TYPESCRIPT: 5_000,
    Language.JAVA: 15_000,
    Language.KOTLIN: 15_000,
}
"""How long a freshly started runner may take to write its `hello` event."""


class RunMode(StrEnum):
    TEST = "test"
    BENCH = "bench"
    """`cstudy bench`: requests and reports are in `coding_study.domain.bench_runs`."""


@dataclass(frozen=True, slots=True)
class FileTarget:
    """Python and TypeScript: the absolute path of the file that defines the target."""

    path: str


@dataclass(frozen=True, slots=True)
class ClassTarget:
    """Java and Kotlin: the fully qualified class, found on the runner's classpath."""

    class_name: str


type RunTarget = FileTarget | ClassTarget


@dataclass(frozen=True, slots=True)
class StressRun:
    """One run of a stress case, fully expanded (docs/specs/runners.md#request)."""

    seed: int
    """The case's seed plus the run index; seeds the per-worker PRNGs."""
    deadline_ms: int
    perturb: Perturbation
    setup: OperationSequence
    """`ops[0]` is the constructor."""
    workers: tuple[OperationSequence, ...]
    """One literal script per worker, in ordinal order; no constructor. Ops may be harness ops."""
    final: OperationSequence | None = None
    """No constructor."""
    thread_kind: ThreadKind | None = None
    """JVM only."""


type RunInput = FunctionInput | OperationSequence
"""Generated cases are materialized into concrete inputs before they reach a request."""

type RequestInput = RunInput | StressRun
"""What one request case carries: stress cases arrive expanded, one `StressRun` per run."""


@dataclass(frozen=True, slots=True)
class RunCase:
    id: str
    input: RequestInput
    hang_guard_ms: int
    """Resolved by the CLI (`resolve_hang_guard_ms`); enforced CLI-side, never sent to runners."""


@dataclass(frozen=True, slots=True)
class RunJob:
    job_id: str
    kind: ProblemKind
    target: RunTarget
    names: SymbolNames
    signature: Signature
    cases: tuple[RunCase, ...]
    model: ConcurrencyModel | None = None
    """Concurrent jobs only."""

    def __post_init__(self) -> None:
        _require_unique((case.id for case in self.cases), f"case id in job {self.job_id}")


@dataclass(frozen=True, slots=True)
class RunRequest:
    """A `test` mode request: every job is loaded once and runs its cases in order."""

    jobs: tuple[RunJob, ...]

    def __post_init__(self) -> None:
        _require_unique((job.job_id for job in self.jobs), "job id")


@dataclass(frozen=True, slots=True)
class UserError:
    """An exception from user code, or why a target could not be loaded."""

    type: str
    message: str
    trace: str = ""
    """Filtered to user frames, at most 10 lines."""


@dataclass(frozen=True, slots=True)
class Returned:
    """`ok`: the target returned; class kinds hold one output per operation."""

    output: JsonValue
    duration_ns: int
    stdout: str = ""


class StressPhase(StrEnum):
    SETUP = "setup"
    WORKER = "worker"
    FINAL = "final"


@dataclass(frozen=True, slots=True)
class WorkerProgress:
    """How far one unfinished worker of a stress run got."""

    worker: int
    """The worker's ordinal."""
    completed: int
    in_op: bool
    """True while inside op `completed`."""


@dataclass(frozen=True, slots=True)
class StressFailure:
    """Where a stress run failed with `error` or `invalid_output`."""

    phase: StressPhase
    op_index: int
    """In the phase's op list (a worker's own script for `worker`)."""
    worker: int | None = None
    """The failing worker's ordinal (phase `worker`)."""
    progress: tuple[WorkerProgress, ...] = ()


@dataclass(frozen=True, slots=True)
class Raised:
    """`error`: the target threw. Class kinds name the failing operation and earlier outputs."""

    error: UserError
    duration_ns: int
    stdout: str = ""
    op_index: int | None = None
    partial_output: tuple[JsonValue, ...] = ()
    stress: StressFailure | None = None
    """Stress runs only."""


@dataclass(frozen=True, slots=True)
class InvalidOutput:
    """The return value cannot be serialized as the declared type."""

    reason: str
    duration_ns: int
    stdout: str = ""
    stress: StressFailure | None = None
    """Stress runs only."""


@dataclass(frozen=True, slots=True)
class SectionCounters:
    """One probe section of a stress run (docs/specs/runners.md#harness-ops)."""

    entries: int
    violations: int
    max_occupancy: int


@dataclass(frozen=True, slots=True)
class StressCompleted:
    """`ok` for a stress run: every worker finished and the final sequence ran."""

    setup: tuple[JsonValue, ...]
    workers: tuple[tuple[JsonValue, ...], ...]
    """One output per op of each worker script, in request order; null for harness ops."""
    final: tuple[JsonValue, ...]
    sections: Mapping[str, SectionCounters]
    duration_ns: int
    """From gate open until the last worker finished."""
    stdout: str = ""


@dataclass(frozen=True, slots=True)
class Stalled:
    """`stalled`: workers were still unfinished at the run's deadline."""

    progress: tuple[WorkerProgress, ...]
    duration_ns: int
    stdout: str = ""


@dataclass(frozen=True, slots=True)
class TimedOut:
    """The hang guard expired; the runner was killed and restarted for the remaining cases."""

    limit_ms: int


@dataclass(frozen=True, slots=True)
class Crashed:
    """The runner process ended during this case (including `System.exit` from user code)."""

    exit_code: int
    stderr_tail: tuple[str, ...] = ()
    """The last 20 lines of the runner's standard error."""


@dataclass(frozen=True, slots=True)
class NotRun:
    reason: str


type CaseOutcome = (
    Returned | Raised | InvalidOutput | TimedOut | Crashed | NotRun | StressCompleted | Stalled
)


@dataclass(frozen=True, slots=True)
class CaseReport:
    case_id: str
    outcome: CaseOutcome


@dataclass(frozen=True, slots=True)
class JobReport:
    """Cases in request order, or a load error that replaces every case of the job."""

    job_id: str
    cases: tuple[CaseReport, ...] = ()
    load_error: UserError | None = None
    restarted_after: tuple[str, ...] = ()
    """Stress runs after which the runner asked to be restarted (leftover threads)."""


@dataclass(frozen=True, slots=True)
class RunnerInfo:
    """From the runner's `hello` event."""

    runner: str
    protocol: int
    runtime: str
    features: tuple[str, ...] = ()
    """Optional protocol additions, e.g. `stress` (docs/specs/runners.md#capability)."""


@dataclass(frozen=True, slots=True)
class RunReport:
    runner: RunnerInfo
    jobs: tuple[JobReport, ...] = ()

    def job(self, job_id: str) -> JobReport:
        return next(job for job in self.jobs if job.job_id == job_id)


def _require_unique(identifiers: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    for identifier in identifiers:
        if identifier in seen:
            raise ValueError(f'duplicate {label} "{identifier}"')
        seen.add(identifier)
