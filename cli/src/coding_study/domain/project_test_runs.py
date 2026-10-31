"""A project's native tests as `cstudy test` reports them (docs/specs/cli.md#project-problems).

The framework's verdict is feedback, never a grade: each test gets a status and an origin, and the
run's tally is what `test_runs` stores. A test in a generated file of an unlocked level is that
level's; one in a file the problem's starter holds is the starter's; any other is yours.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.diagnostics import (
    Diagnostic,
    distinct,
    load_diagnostic,
    report_diagnostic,
)
from coding_study.domain.judging import Tally
from coding_study.domain.runs import Crashed, Raised, TimedOut
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    Skipped,
    SuiteOutcome,
    SuiteReport,
    SuiteTest,
)

TEST_ID_SEPARATOR = "::"
"""Between a test's file and its name: `tests/test_level_1.py::test_ex1`."""


class SuiteStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    """An assertion failed."""
    ERROR = "ERROR"
    """Another exception, a setup failure, a file that does not import, or a crash."""
    SKIP = "SKIP"
    TIMEOUT = "TIMEOUT"


class SuiteOrigin(StrEnum):
    LEVEL = "level"
    """A generated test file of an unlocked level."""
    STARTER = "starter"
    YOURS = "yours"


@dataclass(frozen=True, slots=True)
class SuiteOrigins:
    """Which files of a project folder hold whose tests; paths relative to the folder."""

    level_files: Mapping[str, int]
    """The generated test file of each unlocked level, by path."""
    starter_files: frozenset[str]

    def origin(self, test_id: str) -> tuple[SuiteOrigin, int | None]:
        """The origin of the test's file, and its level when it is a generated file."""
        path = file_of_test(test_id)
        level = self.level_files.get(path)
        if level is not None:
            return SuiteOrigin.LEVEL, level
        if path in self.starter_files:
            return SuiteOrigin.STARTER, None
        return SuiteOrigin.YOURS, None


@dataclass(frozen=True, slots=True)
class SuiteTestVerdict:
    test: SuiteTest
    status: SuiteStatus
    origin: SuiteOrigin
    level: int | None = None
    """The level of a generated test file; None for any other file."""


def file_of_test(test_id: str) -> str:
    """The file a test id names: the id itself for a file that failed to collect."""
    return test_id.partition(TEST_ID_SEPARATOR)[0]


def suite_status(outcome: SuiteOutcome) -> SuiteStatus:
    match outcome:
        case Passed():
            return SuiteStatus.PASS
        case AssertionFailed():
            return SuiteStatus.FAIL
        case Raised() | Crashed():
            return SuiteStatus.ERROR
        case Skipped():
            return SuiteStatus.SKIP
        case TimedOut():
            return SuiteStatus.TIMEOUT


def judge_suite(tests: Iterable[SuiteTest], origins: SuiteOrigins) -> tuple[SuiteTestVerdict, ...]:
    """One verdict per reported test, in run order."""
    return tuple(
        SuiteTestVerdict(test, suite_status(test.outcome), *origins.origin(test.test_id))
        for test in tests
    )


_TALLY_FIELDS = {
    SuiteStatus.PASS: "passed",
    SuiteStatus.FAIL: "failed",
    SuiteStatus.ERROR: "errored",
    SuiteStatus.TIMEOUT: "timed_out",
}


def suite_tally(verdicts: Sequence[SuiteTestVerdict]) -> Tally:
    """What `test_runs` stores: every reported test but skipped ones; `tle` is always 0."""
    counted = [verdict for verdict in verdicts if verdict.status is not SuiteStatus.SKIP]
    counts = dict.fromkeys(_TALLY_FIELDS.values(), 0)
    for verdict in counted:
        counts[_TALLY_FIELDS[verdict.status]] += 1
    return Tally(total=len(counted), **counts)


def suite_diagnostics(report: SuiteReport, root: str) -> tuple[Diagnostic, ...]:
    """Where the project's code did not load: the suite that could not run, read from the
    framework's report with paths under the project folder `root`, then each test file that
    failed to collect (a result whose id is the file), each place once."""
    collected = (
        load_diagnostic(test.outcome.error)
        for test in report.tests
        if isinstance(test.outcome, Raised) and file_of_test(test.test_id) == test.test_id
    )
    refused = report.load_error
    suite = (report_diagnostic(refused, root),) if refused else ()
    return distinct((*suite, *collected))


def unmatched_selections(test_ids: Sequence[str], selections: Sequence[str]) -> tuple[str, ...]:
    """The `cstudy test --case` values that name no reported test: a value names a test by its
    whole id or by its last part (`test_ex1`), as the runner selects them."""
    return tuple(
        selection
        for selection in selections
        if not any(_names(test_id, selection) for test_id in test_ids)
    )


def _names(test_id: str, selection: str) -> bool:
    return test_id == selection or test_id.endswith(f"{TEST_ID_SEPARATOR}{selection}")
