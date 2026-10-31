"""A project's native tests as `cstudy test` reports them (docs/specs/cli.md#project-problems)."""

import pytest

from coding_study.domain.judging import Tally
from coding_study.domain.project_test_runs import (
    SuiteOrigin,
    SuiteOrigins,
    SuiteStatus,
    judge_suite,
    suite_status,
    suite_tally,
    unmatched_selections,
)
from coding_study.domain.runs import Crashed, Raised, TimedOut, UserError
from coding_study.domain.suite_runs import AssertionFailed, Passed, Skipped, SuiteTest

ORIGINS = SuiteOrigins(
    level_files={"tests/test_level_1.py": 1, "tests/test_level_2.py": 2},
    starter_files=frozenset({"tests/test_models.py", "bank/bank.py"}),
)
ERROR = UserError("ImportError", "no module named bank")


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (Passed(1000), SuiteStatus.PASS),
        (AssertionFailed("assert 1 == 2", 1000), SuiteStatus.FAIL),
        (Raised(ERROR, 1000), SuiteStatus.ERROR),
        (Skipped("later", 0), SuiteStatus.SKIP),
        (TimedOut(10_000), SuiteStatus.TIMEOUT),
        (Crashed(1), SuiteStatus.ERROR),
    ],
)
def test_each_outcome_has_its_status(outcome, status):
    assert suite_status(outcome) is status


@pytest.mark.parametrize(
    ("test_id", "origin"),
    [
        ("tests/test_level_2.py::test_ex3", (SuiteOrigin.LEVEL, 2)),
        ("tests/test_models.py::test_account", (SuiteOrigin.STARTER, None)),
        ("tests/test_overdraft.py::test_refuses", (SuiteOrigin.YOURS, None)),
        ("tests/test_level_1.py", (SuiteOrigin.LEVEL, 1)),
        ("tests/test_level_3.py::test_ex5", (SuiteOrigin.YOURS, None)),
    ],
)
def test_a_test_takes_the_origin_of_its_file(test_id, origin):
    assert ORIGINS.origin(test_id) == origin


def test_judging_keeps_the_run_order():
    tests = (SuiteTest("b.py::test_b", Passed(1)), SuiteTest("a.py::test_a", Passed(1)))
    assert [verdict.test.test_id for verdict in judge_suite(tests, ORIGINS)] == [
        "b.py::test_b",
        "a.py::test_a",
    ]


def test_judging_tags_each_test_with_its_status_origin_and_level():
    (verdict,) = judge_suite(
        (SuiteTest("tests/test_level_2.py::test_ex3", AssertionFailed("assert 1", 5)),), ORIGINS
    )
    assert (verdict.status, verdict.origin, verdict.level) == (
        SuiteStatus.FAIL,
        SuiteOrigin.LEVEL,
        2,
    )


def test_the_tally_leaves_skipped_tests_out():
    verdicts = judge_suite(
        (
            SuiteTest("t.py::a", Passed(1)),
            SuiteTest("t.py::b", AssertionFailed("assert 0", 1)),
            SuiteTest("t.py::c", Raised(ERROR, 1)),
            SuiteTest("t.py::d", Crashed(1)),
            SuiteTest("t.py::e", TimedOut(10)),
            SuiteTest("t.py::f", Skipped("no", 0)),
        ),
        ORIGINS,
    )
    assert suite_tally(verdicts) == Tally(total=5, passed=1, failed=1, errored=2, timed_out=1)


@pytest.mark.parametrize("selection", ["tests/test_level_1.py::test_ex1", "test_ex1"])
def test_a_selection_matches_a_whole_id_or_its_last_part(selection):
    assert unmatched_selections(("tests/test_level_1.py::test_ex1",), (selection,)) == ()


def test_a_selection_must_be_a_whole_last_part():
    assert unmatched_selections(("tests/test_level_1.py::test_ex10",), ("test_ex1",)) == (
        "test_ex1",
    )


def test_every_selection_without_a_test_is_reported():
    assert unmatched_selections(("t.py::test_a",), ("test_a", "test_b", "test_c")) == (
        "test_b",
        "test_c",
    )
