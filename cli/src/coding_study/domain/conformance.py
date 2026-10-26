"""Expected runner outcomes for the conformance suite (docs/specs/runners.md#conformance-suite).

Fixtures are ordinary problems under runners/conformance/; every language's reference approach
for a fixture must produce these outcomes when run through its runner.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from coding_study.domain.cases import JsonValue


class ExpectedStatus(StrEnum):
    PASS = "pass"
    """Runner status `ok` and the problem's comparator accepts the output."""
    ERROR = "error"
    INVALID_OUTPUT = "invalid_output"
    TIMEOUT = "timeout"
    LOAD_ERROR = "load_error"
    """Applies to the whole job: the runner reports `load_error` instead of any case."""
    FAIL = "fail"
    """Stress cases: the run completed but broke an invariant or `final.expected`."""
    STALLED = "stalled"
    """Stress cases: workers were still unfinished at the deadline."""


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    status: ExpectedStatus
    message: str | None = None
    """`error`: the exact exception message."""
    op_index: int | None = None
    partial_output: tuple[JsonValue, ...] | None = None
    stdout: str | None = None
    """`pass`: the exact captured standard output."""
    runs: int | None = None
    """Stress cases: runs per variant (default 10)."""
    min_failed: int | None = None
    """Stress cases: at least this many runs fail with `status` (default: every run)."""
    max_failed: int | None = None
    """Stress cases: at most this many runs fail (with `pass`: default 0)."""
    phase: str | None = None
    """Stress `error`: the failing phase, `setup`, `worker` or `final`."""
    deterministic: bool = False
    """Stress cases: a repeated seed gives an identical run record, and the runs differ."""
    restart_requested: bool = False
    """Stress cases: the runner asked to be restarted after the case's runs."""


@dataclass(frozen=True, slots=True)
class ConformanceExpectation:
    slug: str
    approach_id: str
    outcome: ExpectedOutcome
    case_outcomes: Mapping[str, ExpectedOutcome] = field(default_factory=dict[str, ExpectedOutcome])

    def outcome_for(self, case_id: str) -> ExpectedOutcome:
        return self.case_outcomes.get(case_id, self.outcome)


@dataclass(frozen=True, slots=True)
class ConformanceSuite:
    problems_directory: str
    """Repository-relative directory of the fixture problems."""
    expectations: tuple[ConformanceExpectation, ...]
