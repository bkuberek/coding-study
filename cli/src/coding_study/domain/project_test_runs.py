"""A project's native tests as `cstudy test` reports them (docs/specs/cli.md#project-problems).

The framework's verdict is feedback, never a grade: each test gets a status and an origin, and the
run's tally is what `test_runs` stores. A test in a generated file of an unlocked level is that
level's; one in a file the problem's starter holds is the starter's; any other is yours.
"""

import posixpath
from collections.abc import Container, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.diagnostics import (
    Diagnostic,
    distinct,
    load_diagnostic,
    report_diagnostic,
)
from coding_study.domain.judging import Tally
from coding_study.domain.project import ProjectTree
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
"""Between a test's file and its name: `tests/test_level_1.py::test_ex1`; in Rust, also between
the modules of a libtest name."""
_RUST_EXTENSION = ".rs"
_RUST_MODULE_FILE = "mod.rs"
_RUST_TEST_ATTRIBUTE = "#[test]"


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
    """The starter's files that hold its tests: all of them, but in Rust only those that declare
    a test (`rust_starter_test_files`)."""
    module_files: frozenset[str] | None = None
    """Rust: the folder's files, where a test's module path finds the file that declares it
    (`rust_test_file`); None for the languages whose test ids name that file."""

    def origin(self, test_id: str) -> tuple[SuiteOrigin, int | None]:
        """The origin of the test's file, and its level when it is a generated file."""
        path = self._declaring_file(test_id)
        level = self.level_files.get(path)
        if level is not None:
            return SuiteOrigin.LEVEL, level
        if path in self.starter_files:
            return SuiteOrigin.STARTER, None
        return SuiteOrigin.YOURS, None

    def _declaring_file(self, test_id: str) -> str:
        if self.module_files is None:
            return file_of_test(test_id)
        return rust_test_file(test_id, self.module_files)


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


def rust_test_file(test_id: str, files: Container[str]) -> str:
    """The file that declares a Rust test. Its id names the target, then the libtest name, whose
    module path leads to the innermost module with a file of its own, `<module>.rs` or
    `<module>/mod.rs` from the target's directory, as `mod` declarations find them:
    `src/lib.rs::ledger::tests::posts` is declared in `src/ledger.rs`. A test of the target's own
    module, or of a module written inline in it, is declared in the target."""
    target, _, name = test_id.partition(TEST_ID_SEPARATOR)
    modules = name.split(TEST_ID_SEPARATOR)[:-1]
    directory = posixpath.dirname(target)
    for depth in range(len(modules), 0, -1):
        module = posixpath.join(directory, *modules[:depth])
        for candidate in (f"{module}{_RUST_EXTENSION}", f"{module}/{_RUST_MODULE_FILE}"):
            if candidate in files:
                return candidate
    return target


def rust_starter_test_files(starter: ProjectTree) -> frozenset[str]:
    """The starter's Rust files that declare a test. A Rust source file also holds unit tests, so
    a test added to a starter file that came without tests is yours."""
    return frozenset(
        file.path
        for file in starter.files
        if file.path.endswith(_RUST_EXTENSION) and file.text and _RUST_TEST_ATTRIBUTE in file.text
    )


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
