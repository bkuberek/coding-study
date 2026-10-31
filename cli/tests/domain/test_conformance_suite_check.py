"""Suite expectations of the conformance suite: the outcome of every test a project's native
suite runs (runners/conformance/expectations.json, docs/specs/runners.md#conformance-suite)."""

from coding_study.domain.conformance import ExpectedTest, ExpectedTestStatus
from coding_study.domain.conformance_check import suite_mismatches
from coding_study.domain.runs import Crashed, Raised, RunnerInfo, TimedOut, UserError
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    Skipped,
    SuiteOutcome,
    SuiteReport,
    SuiteTest,
)

RUNNER = RunnerInfo("python", 1, "3.13", ("project", "suite"))
OK, FAILED, ERROR = ExpectedTestStatus.OK, ExpectedTestStatus.FAILED, ExpectedTestStatus.ERROR
SKIPPED, TIMEOUT, CRASHED = (
    ExpectedTestStatus.SKIPPED,
    ExpectedTestStatus.TIMEOUT,
    ExpectedTestStatus.CRASHED,
)
PASSES = "tests/test_statuses.py::test_passes"
RAISES = "tests/test_statuses.py::test_raises"


def report(*tests: tuple[str, SuiteOutcome], **fields: object) -> SuiteReport:
    reported = tuple(SuiteTest(test_id, outcome) for test_id, outcome in tests)
    return SuiteReport(RUNNER, reported, **fields)  # type: ignore[arg-type]


def raised(message: str) -> Raised:
    return Raised(UserError("RuntimeError", message), 1_000)


def test_every_status_matches_its_outcome():
    expected = {
        "a": ExpectedTest(OK),
        "b": ExpectedTest(FAILED),
        "c": ExpectedTest(ERROR),
        "d": ExpectedTest(SKIPPED),
        "e": ExpectedTest(TIMEOUT),
        "f": ExpectedTest(CRASHED),
    }
    outcomes: tuple[tuple[str, SuiteOutcome], ...] = (
        ("a", Passed(1_000)),
        ("b", AssertionFailed("assert 1 == 2", 1_000)),
        ("c", raised("boom")),
        ("d", Skipped("not today", 1_000)),
        ("e", TimedOut(1_000)),
        ("f", Crashed(3)),
    )
    assert suite_mismatches(expected, report(*outcomes)) == []


def test_another_status_is_a_mismatch():
    expected = {PASSES: ExpectedTest(OK)}
    assert suite_mismatches(expected, report((PASSES, raised("boom")))) == [
        f"{PASSES}: expected ok, got error"
    ]


def test_an_error_message_must_match_exactly():
    expected = {RAISES: ExpectedTest(ERROR, message="conformance failure")}
    assert suite_mismatches(expected, report((RAISES, raised("other")))) == [
        f'{RAISES}: expected message "conformance failure", got "other"'
    ]


def test_a_failure_message_must_match_exactly():
    expected = {PASSES: ExpectedTest(FAILED, message="assert 1 == 2")}
    actual = report((PASSES, AssertionFailed("assert 1 == 3", 1_000)))
    assert suite_mismatches(expected, actual) == [
        f'{PASSES}: expected message "assert 1 == 2", got "assert 1 == 3"'
    ]


def test_captured_output_must_match_exactly():
    expected = {PASSES: ExpectedTest(OK, stdout="conformance output\n")}
    assert suite_mismatches(expected, report((PASSES, Passed(1_000, "other\n")))) == [
        f'{PASSES}: expected stdout "conformance output\\n", got "other\\n"'
    ]


def test_a_test_that_was_not_reported_is_a_mismatch():
    expected = {PASSES: ExpectedTest(OK), RAISES: ExpectedTest(ERROR)}
    assert suite_mismatches(expected, report((PASSES, Passed(1_000)))) == [
        f"{RAISES}: expected error, not reported"
    ]


def test_an_unexpected_test_is_a_mismatch():
    expected = {PASSES: ExpectedTest(OK)}
    actual = report((PASSES, Passed(1_000)), (RAISES, raised("boom")))
    assert suite_mismatches(expected, actual) == [f"{RAISES}: not expected, got error"]


def test_a_test_reported_twice_is_a_mismatch():
    expected = {PASSES: ExpectedTest(OK)}
    actual = report((PASSES, Passed(1_000)), (PASSES, Passed(1_000)))
    assert suite_mismatches(expected, actual) == [f"{PASSES}: reported 2 times"]


def test_a_suite_that_did_not_run_is_a_mismatch():
    expected = {PASSES: ExpectedTest(OK)}
    actual = report(load_error=UserError("UsageError", "no such option"))
    assert suite_mismatches(expected, actual) == [
        "suite did not run: UsageError: no such option",
    ]


def test_a_suite_that_stopped_early_is_a_mismatch():
    expected = {PASSES: ExpectedTest(OK)}
    actual = report((PASSES, Passed(1_000)), stopped_early="the runner crashed 4 times")
    assert suite_mismatches(expected, actual) == ["suite stopped early: the runner crashed 4 times"]
