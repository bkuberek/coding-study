"""What one test's process says about its outcome (docs/specs/runners.md#rust-projects): the exit
code first, then libtest's own lines, recorded from real runs of `<binary> --exact <name>
--nocapture` with standard output and error in one pipe."""

from pathlib import Path

import pytest

from coding_study.adapters.languages.rust.libtest import (
    FinishedTest,
    finished_outcome,
    listed_tests,
)
from coding_study.domain.runs import Crashed, Raised, UserError
from coding_study.domain.suite_runs import AssertionFailed, Passed, Skipped

ROOT = Path("/ws/projects/bank")
SUMMARY_OK = (
    "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 9 filtered out; "
    "finished in 0.00s\n\n"
)
NOTE = "note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace\n"
FAILED_TAIL = (
    "\nfailures:\n\nfailures:\n    {name}\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; "
    "0 measured; 9 filtered out; finished in 0.00s\n\n"
)
PASSED = "\nrunning 1 test\nhello out\nhello err\ntest ok ... ok\n\n" + SUMMARY_OK
ASSERTION = (
    "\nrunning 1 test\n\nthread 'fails' (213405354) panicked at tests/level_1.rs:6:33:\n"
    "assertion `left == right` failed: custom 1\n  left: 3\n right: 4\n"
    + NOTE
    + "partialtest fails ... FAILED\n"
    + FAILED_TAIL.format(name="fails")
)
IGNORED = (
    "\nrunning 1 test\ntest ignored_reason ... ignored, not today\n\ntest result: ok. 0 passed; "
    "0 failed; 1 ignored; 0 measured; 9 filtered out; finished in 0.00s\n\n"
)
IGNORED_PLAIN = IGNORED.replace("ignored_reason ... ignored, not today", "plain ... ignored")
SHOULD_PANIC = (
    "\nrunning 1 test\n\nthread 'should' (213406106) panicked at tests/level_1.rs:15:15:\nboom\n"
    + NOTE
    + "test should - should panic ... ok\n\n"
    + SUMMARY_OK
)
DID_NOT_PANIC = (
    "\nrunning 1 test\ntest should_not - should panic ... FAILED\n\nfailures:\n\n"
    "---- should_not stdout ----\nnote: test did not panic as expected at tests/level_1.rs:18:4\n"
    "\nfailures:\n    should_not\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; "
    "0 measured; 9 filtered out; finished in 0.00s\n\n"
)
RETURNED_ERR = (
    '\nrunning 1 test\nError: "bad result"\ntest result_err ... FAILED\n'
    + FAILED_TAIL.format(name="result_err")
)
MULTILINE = (
    "\nrunning 1 test\nbefore\n\nthread 'multiline' (2134) panicked at "
    "/ws/projects/bank/src/lib.rs:30:18:\nline one\nline two\n"
    + NOTE
    + "test multiline ... FAILED\n"
) + FAILED_TAIL.format(name="multiline")
ABORTED = "\nrunning 1 test\nlast words\n"
DURATION = 41_000


def outcome(name: str, exit_code: int, output: str):
    return finished_outcome(name, FinishedTest(exit_code, output, DURATION), ROOT)


# listing


def test_a_listing_names_each_test_in_its_order():
    listing = "tests::b: test\nledger::tests::a: test\n"
    assert listed_tests(listing) == ("tests::b", "ledger::tests::a")


def test_a_listing_leaves_out_benchmarks_and_other_lines():
    listing = "0 tests, 0 benchmarks\nbench_x: benchmark\nok: test\n\n"
    assert listed_tests(listing) == ("ok",)


# outcomes


def test_a_passing_test_is_ok_with_what_it_printed():
    assert outcome("ok", 0, PASSED) == Passed(DURATION, "hello out\nhello err\n")


def test_a_failed_assertion_is_failed_with_the_panic_and_its_location():
    assert outcome("fails", 101, ASSERTION) == AssertionFailed(
        "assertion `left == right` failed: custom 1\n  left: 3\n right: 4\n"
        "at tests/level_1.rs:6:33",
        DURATION,
        "partial",
    )


def test_a_panic_location_in_the_project_is_relative_to_its_root():
    found = outcome("multiline", 101, MULTILINE)
    assert isinstance(found, AssertionFailed)
    assert found.message == "line one\nline two\nat src/lib.rs:30:18"


def test_a_panic_leaves_what_the_test_printed_before_it_as_its_output():
    found = outcome("multiline", 101, MULTILINE)
    assert isinstance(found, AssertionFailed)
    assert found.stdout == "before\n"


def test_an_ignored_test_is_skipped_with_its_reason():
    assert outcome("ignored_reason", 0, IGNORED) == Skipped("not today", DURATION)


def test_an_ignored_test_without_a_reason_says_ignored():
    assert outcome("plain", 0, IGNORED_PLAIN) == Skipped("ignored", DURATION)


def test_a_should_panic_test_that_panics_is_ok_without_the_panic_in_its_output():
    assert outcome("should", 0, SHOULD_PANIC) == Passed(DURATION)


def test_a_should_panic_test_that_does_not_panic_fails_with_libtests_note():
    assert outcome("should_not", 101, DID_NOT_PANIC) == AssertionFailed(
        "note: test did not panic as expected at tests/level_1.rs:18:4", DURATION
    )


def test_a_test_that_returns_an_error_fails_with_it():
    assert outcome("result_err", 101, RETURNED_ERR) == AssertionFailed(
        'Error: "bad result"', DURATION
    )


@pytest.mark.parametrize("exit_code", [134, 3, 139])
def test_any_other_exit_is_a_crash_of_that_test(exit_code):
    assert outcome("aborts", exit_code, ABORTED) == Crashed(exit_code, ("last words",))


def test_a_crash_keeps_the_last_20_lines_of_output():
    output = "\nrunning 1 test\n" + "".join(f"line {number}\n" for number in range(30))
    found = outcome("aborts", 134, output)
    assert isinstance(found, Crashed)
    assert found.stderr_tail == tuple(f"line {number}" for number in range(10, 30))


def test_a_test_that_did_not_run_is_an_error():
    output = "\nrunning 0 tests\n\ntest result: ok. 0 passed; 0 failed; 0 ignored\n\n"
    assert outcome("gone", 0, output) == Raised(
        UserError("libtest", "the test did not run: libtest found no test named gone"), DURATION
    )


def test_a_failure_without_libtests_result_line_is_an_error_with_its_output():
    output = "error: Unrecognized option: 'nocapture'\n"
    assert outcome("ok", 101, output) == Raised(
        UserError("libtest", "error: Unrecognized option: 'nocapture'"), DURATION
    )


def test_output_beyond_4_kib_is_truncated_with_a_notice():
    long = "\nrunning 1 test\n" + "x" * 5000 + "\ntest ok ... ok\n\n" + SUMMARY_OK
    found = outcome("ok", 0, long)
    assert isinstance(found, Passed)
    assert found.stdout == "x" * 4096 + "\n[output truncated at 4 KiB]\n"
