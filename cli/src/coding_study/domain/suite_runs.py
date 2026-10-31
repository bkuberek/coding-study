"""A project's native test suite, as the CLI asks a runner to run it and what came back
(docs/specs/runners.md#suite-job).

The framework discovers the tests, so a suite job has no cases: its report holds one result per
test the runner reported, in the order they ran. A suite result is the framework's verdict on code
the user may edit: feedback, never a grade, so no comparator judges it.
"""

from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.cases import JsonValue
from coding_study.domain.runs import Crashed, Raised, RunnerInfo, TimedOut, UserError


class SuiteFramework(StrEnum):
    PYTEST = "pytest"
    NODE_TEST = "node-test"
    GO_TEST = "go-test"


@dataclass(frozen=True, slots=True)
class SuiteJob:
    job_id: str
    framework: SuiteFramework
    root: str
    """The project root, absolute."""
    hang_guard_ms: int
    """Per test; resolved by the CLI (`resolve_hang_guard_ms`) and enforced CLI-side."""
    exclude: tuple[str, ...] = ()
    """Files, relative to the root, not to run: the generated test files of locked levels."""
    select: tuple[str, ...] = ()
    """Test ids, or their last part, to run (`cstudy test --case`); empty: every test."""


@dataclass(frozen=True, slots=True)
class Passed:
    """`ok`: the test passed."""

    duration_ns: int
    stdout: str = ""


@dataclass(frozen=True, slots=True)
class Comparison:
    """Both sides of a failed assertion, when the framework reports them as JSON values."""

    expected: JsonValue
    actual: JsonValue


@dataclass(frozen=True, slots=True)
class AssertionFailed:
    """`failed`: an assertion failed; `message` is the framework's text, such as
    `assert -1 == 5`."""

    message: str
    duration_ns: int
    stdout: str = ""
    comparison: Comparison | None = None


@dataclass(frozen=True, slots=True)
class Skipped:
    """`skipped`: the framework skipped the test, for the reason in `message`."""

    message: str
    duration_ns: int
    stdout: str = ""


type SuiteResult = Passed | AssertionFailed | Raised | Skipped
"""What a runner reports for one test; `Raised` is any other exception, a setup failure, or a
test file that does not import (whose id is the file)."""
type SuiteOutcome = SuiteResult | TimedOut | Crashed
"""A hang or crash is recorded on the test in progress, which a restart then leaves out."""


@dataclass(frozen=True, slots=True)
class SuiteTest:
    test_id: str
    """The framework's id: pytest's node id, such as `tests/test_level_1.py::test_ex1`."""
    outcome: SuiteOutcome


@dataclass(frozen=True, slots=True)
class SuiteReport:
    runner: RunnerInfo
    tests: tuple[SuiteTest, ...] = ()
    """In the order they ran, across restarts."""
    load_error: UserError | None = None
    """The framework could not run the suite at all (for example unusable options)."""
    stopped_early: str | None = None
    """Why the tests not reported yet never ran, such as restarts running out; None when the
    suite ran to its end."""
