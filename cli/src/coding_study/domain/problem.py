"""Autograded problems as described by meta.yaml (docs/specs/problem-format.md#metayaml)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from coding_study.domain.cases import Case
from coding_study.domain.signature import Signature
from coding_study.domain.time_limits import TimeLimit

if TYPE_CHECKING:
    from coding_study.domain.concurrency import Concurrency

DEFAULT_FLOAT_TOLERANCE = 1e-6
DEFAULT_SIZE_LADDER = (100, 1000, 10000, 100000)
DEFAULT_BUDGET_MS = 2000
DEFAULT_CURRICULUM_ORDER = 1000


class Language(StrEnum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    KOTLIN = "kotlin"
    GO = "go"
    RUST = "rust"


CORE_LANGUAGES = (Language.PYTHON, Language.TYPESCRIPT, Language.JAVA, Language.KOTLIN)
"""What a problem lists unless it says otherwise, and what "every language" means in defaults and
coverage: the languages every problem has references in."""
OPTIONAL_LANGUAGES = (Language.GO, Language.RUST)
"""Problems opt in by listing them in `languages` (docs/decisions/0012-go-and-rust.md)."""


class Track(StrEnum):
    DSA = "dsa"
    PRACTICAL = "practical"
    LLD = "lld"
    CONCURRENCY = "concurrency"
    DEBUGGING = "debugging"
    SYSTEM_DESIGN = "system-design"
    CODE_REVIEW = "code-review"
    BEHAVIORAL = "behavioral"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ProblemKind(StrEnum):
    FUNCTION = "function"
    DESIGN = "design"
    PROGRESSIVE = "progressive"
    CONCURRENT = "concurrent"


class StubSource(StrEnum):
    GENERATED = "generated"
    BUGGY = "buggy"


class ApproachRole(StrEnum):
    BRUTE = "brute"
    INTERMEDIATE = "intermediate"
    OPTIMAL = "optimal"


class ComplexityClass(StrEnum):
    """Growth classes in ladder order, slowest-growing first."""

    CONSTANT = "1"
    LOGARITHMIC = "log n"
    SQUARE_ROOT = "sqrt n"
    LINEAR = "n"
    LINEARITHMIC = "n log n"
    QUADRATIC = "n^2"
    QUADRATIC_LOGARITHMIC = "n^2 log n"
    CUBIC = "n^3"
    EXPONENTIAL = "2^n"
    FACTORIAL = "n!"


class ComparatorType(StrEnum):
    EXACT = "exact"
    UNORDERED = "unordered"
    UNORDERED_NESTED = "unordered-nested"
    FLOAT = "float"
    CHECKER = "checker"
    OPS = "ops"


@dataclass(frozen=True, slots=True)
class ComparatorSpec:
    type: ComparatorType
    tolerance: float = DEFAULT_FLOAT_TOLERANCE
    per_method: Mapping[str, ComparatorType] = field(default_factory=dict[str, ComparatorType])


@dataclass(frozen=True, slots=True)
class Approach:
    id: str
    name: str
    role: ApproachRole
    time: str
    space: str
    time_class: ComplexityClass | None
    """None only for concurrent problems, which declare no complexity classes."""
    space_class: ComplexityClass | None
    oracle: bool = False


@dataclass(frozen=True, slots=True)
class Level:
    number: int
    title: str


@dataclass(frozen=True, slots=True)
class Perf:
    size_param: str | None = None
    size_ladder: tuple[int, ...] = DEFAULT_SIZE_LADDER
    budget_ms: int = DEFAULT_BUDGET_MS
    expected_from: str | None = None
    time_limit: TimeLimit | None = None


@dataclass(frozen=True, slots=True)
class LeetCodeReference:
    number: int
    url: str


@dataclass(frozen=True, slots=True)
class References:
    leetcode: LeetCodeReference | None = None
    links: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProblemMeta:
    id: str
    slug: str
    title: str
    status: ContentStatus
    difficulty: Difficulty
    track: Track
    kind: ProblemKind
    signature: Signature
    comparator: ComparatorSpec
    approaches: tuple[Approach, ...]
    patterns: tuple[str, ...] = ()
    languages: tuple[Language, ...] = CORE_LANGUAGES
    stub: StubSource = StubSource.GENERATED
    levels: tuple[Level, ...] = ()
    perf: Perf = Perf()
    hang_guard_ms: int | None = None
    references: References = References()
    related: tuple[str, ...] = ()
    order: int = DEFAULT_CURRICULUM_ORDER
    estimate_minutes: int | None = None
    concurrency: "Concurrency | None" = None
    """Concurrent problems only (docs/specs/problem-format.md#concurrent-problems)."""

    @property
    def directory_name(self) -> str:
        return f"{self.id}-{self.slug}"

    @property
    def snake_slug(self) -> str:
        return self.slug.replace("-", "_")


@dataclass(frozen=True, slots=True)
class Problem:
    meta: ProblemMeta
    cases: tuple[Case, ...]


@dataclass(frozen=True, slots=True)
class ProblemSummary:
    """What `cstudy list` needs without reading tests.json."""

    meta: ProblemMeta
    directory: str
    """Repository-relative, e.g. `problems/0001-two-sum`."""
    reference_languages: tuple[Language, ...]
    """Languages with at least one reference file for a declared approach, in `Language` order."""
