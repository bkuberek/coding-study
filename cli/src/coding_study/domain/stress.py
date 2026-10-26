"""Stress cases of concurrent problems as written in tests.json.

Spec: docs/specs/problem-format.md#stress-cases. A scenario is a single-threaded setup, worker
groups whose op scripts are released together, an optional quiescent final sequence, and the
invariants every run must satisfy. Templates stay unexpanded here; `stress_expansion` turns them
into literal per-worker scripts for one run.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from coding_study.domain.cases import JsonValue, OperationSequence
from coding_study.domain.concurrency import PerturbationOverride
from coding_study.domain.problem import Language

DEFAULT_STRESS_SEED = 1
HARNESS_PREFIX = "@"


class HarnessOp(StrEnum):
    """Ops the runner implements itself (docs/specs/problem-format.md#harness-ops)."""

    ENTER = "@enter"
    EXIT = "@exit"
    PAUSE = "@pause"


HARNESS_ARITY: Mapping[HarnessOp, int] = {HarnessOp.ENTER: 2, HarnessOp.EXIT: 1, HarnessOp.PAUSE: 1}
SECTION_MODES = ("exclusive", "shared")
MAX_PAUSE = 1000


def is_harness_op(op: str) -> bool:
    return op.startswith(HARNESS_PREFIX)


@dataclass(frozen=True, slots=True)
class Literal:
    value: JsonValue


@dataclass(frozen=True, slots=True)
class ArithmeticSequence:
    """`$seq`: `start + worker * worker_stride + iteration * step`."""

    start: int
    worker_stride: int = 0
    step: int = 1


@dataclass(frozen=True, slots=True)
class RandomInteger:
    """`$rand`: a uniform integer in `[low, high]`."""

    low: int
    high: int


@dataclass(frozen=True, slots=True)
class Pick:
    """`$pick`: one of the listed values, uniformly."""

    values: tuple[JsonValue, ...]


type Template = Literal | ArithmeticSequence | RandomInteger | Pick


@dataclass(frozen=True, slots=True)
class Step:
    op: str
    args: tuple[Template, ...]
    weight: int = 1
    """Only meaningful inside a `mix`."""


@dataclass(frozen=True, slots=True)
class Repeat:
    """Iterations per worker, optionally different per language."""

    default: int
    per_language: Mapping[Language, int] = field(default_factory=dict[Language, int])

    def for_language(self, language: Language) -> int:
        return self.per_language.get(language, self.default)

    @property
    def largest(self) -> int:
        return max((self.default, *self.per_language.values()))


@dataclass(frozen=True, slots=True)
class WorkerGroup:
    group: str
    count: int
    repeat: Repeat
    steps: tuple[Step, ...]
    is_mix: bool = False
    """True: every iteration runs one step chosen by weight; False: all steps in order."""


@dataclass(frozen=True, slots=True)
class FinalSequence:
    """Ops run single-threaded after every worker finished; no constructor."""

    ops: tuple[str, ...]
    args: tuple[tuple[JsonValue, ...], ...]
    expected: tuple[JsonValue, ...] | None = None

    @property
    def sequence(self) -> OperationSequence:
        return OperationSequence(self.ops, self.args)


class Scope(StrEnum):
    SETUP = "setup"
    WORKERS = "workers"
    FINAL = "final"
    ALL = "all"


OUTPUT = "output"
ARGUMENT_PREFIX = "arg"


@dataclass(frozen=True, slots=True)
class Selector:
    """Which recorded values an invariant reads (docs/specs/problem-format.md#selectors)."""

    op: str
    of: str = OUTPUT
    """`output`, or `arg0`, `arg1`, ... for an argument."""
    group: str | None = None
    scope: Scope = Scope.ALL

    @property
    def argument_index(self) -> int | None:
        """None when the selector reads outputs."""
        if self.of == OUTPUT:
            return None
        return int(self.of.removeprefix(ARGUMENT_PREFIX))

    def label(self) -> str:
        """How failure reasons name it, e.g. `put.arg0`, `take[consumer]`, `size@final`."""
        text = self.op if self.of == OUTPUT else f"{self.op}.{self.of}"
        if self.group is not None:
            text += f"[{self.group}]"
        if self.scope is not Scope.ALL:
            text += f"@{self.scope}"
        return text


@dataclass(frozen=True, slots=True)
class EqualMultisets:
    left: Selector
    right: Selector


@dataclass(frozen=True, slots=True)
class Distinct:
    values: Selector


@dataclass(frozen=True, slots=True)
class Bounds:
    values: Selector
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, slots=True)
class Count:
    values: Selector
    equals: int | None = None
    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True, slots=True)
class Sum:
    values: Selector
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, slots=True)
class SourceOrder:
    values: Selector
    stride: int


@dataclass(frozen=True, slots=True)
class SectionBounds:
    name: str
    max_violations: int = 0
    min_occupancy: int | None = None
    max_occupancy: int | None = None


@dataclass(frozen=True, slots=True)
class CheckerInvariant:
    name: str


type Invariant = (
    EqualMultisets
    | Distinct
    | Bounds
    | Count
    | Sum
    | SourceOrder
    | SectionBounds
    | CheckerInvariant
)


INVARIANT_TYPES: Mapping[type, str] = {
    EqualMultisets: "equal_multisets",
    Distinct: "distinct",
    Bounds: "bounds",
    Count: "count",
    Sum: "sum",
    SourceOrder: "source_order",
    SectionBounds: "section",
    CheckerInvariant: "checker",
}
"""Each invariant's `type` as tests.json writes it."""


def invariant_type(invariant: Invariant) -> str:
    return INVARIANT_TYPES[type(invariant)]


def invariant_selectors(invariant: Invariant) -> tuple[Selector, ...]:
    match invariant:
        case EqualMultisets(left=left, right=right):
            return (left, right)
        case Distinct(values=values) | Bounds(values=values) | Count(values=values):
            return (values,)
        case Sum(values=values) | SourceOrder(values=values):
            return (values,)
        case SectionBounds() | CheckerInvariant():
            return ()


@dataclass(frozen=True, slots=True)
class StressScenario:
    """A stress case's `stress` object."""

    setup: OperationSequence
    workers: tuple[WorkerGroup, ...]
    invariants: tuple[Invariant, ...] = ()
    final: FinalSequence | None = None
    seed: int = DEFAULT_STRESS_SEED
    deadline_ms: int | None = None
    """None: `concurrency.deadline_ms`."""
    perturb: PerturbationOverride = field(default_factory=PerturbationOverride)
    document: Mapping[str, JsonValue] = field(default_factory=dict[str, JsonValue])
    """The object as written in tests.json; `stress_checker.py` receives it."""

    @property
    def worker_count(self) -> int:
        return sum(group.count for group in self.workers)

    def ops_per_run(self, language: Language) -> int:
        """Setup, worker and final ops after expansion in `language`."""
        worker_ops = sum(
            group.count * group.repeat.for_language(language) * _ops_per_iteration(group)
            for group in self.workers
        )
        final_ops = len(self.final.ops) if self.final else 0
        return len(self.setup.ops) + worker_ops + final_ops


def _ops_per_iteration(group: WorkerGroup) -> int:
    return 1 if group.is_mix else len(group.steps)
