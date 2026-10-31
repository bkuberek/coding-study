"""Project submissions and the grade rules of project attempts
(docs/specs/progress-and-scheduling.md#project-attempts)."""

from datetime import UTC, datetime, timedelta

import pytest

from coding_study.domain.attempts import Grade
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected, OperationSequence
from coding_study.domain.judging import CaseVerdict, Judgement, RunnableCase, Tally
from coding_study.domain.runs import Returned, UserError
from coding_study.domain.submissions import (
    LevelTally,
    SubmissionRecord,
    best_per_level,
    counted_submission,
    level_grade_cap,
    level_tallies,
    levels_finished,
)

SUBMITTED = datetime(2026, 10, 30, 18, 0, tzinfo=UTC)
OPS = OperationSequence(("Bank",), ((),))


def case(case_id: str, level: int, visible: bool = False) -> Case:
    return Case(case_id, OPS, Expected([None]), visible=visible, level=level)


def verdict(graded: Case, status: CaseStatus) -> CaseVerdict:
    runnable = RunnableCase(graded.id, OPS, graded.expected, visible=graded.visible)
    return CaseVerdict(runnable, status, Returned([None], 1000))


CASES = (case("ex1", 1, True), case("h1", 1), case("h2", 1), case("ex2", 2, True), case("h3", 2))


def tally(level: int, passed: int, total: int = 2) -> LevelTally:
    return LevelTally(level, 1, min(passed, 1), total - 1, max(passed - 1, 0))


def submission(*levels: LevelTally, every_level: bool = True, minutes: int = 0) -> SubmissionRecord:
    return SubmissionRecord(
        attempt_id=1,
        submitted_at=SUBMITTED + timedelta(minutes=minutes),
        code_hash="abc",
        graded_up_to=len(levels),
        every_level=every_level,
        levels=levels,
        tally=Tally(total=sum(level.total for level in levels)),
        duration_ms=300,
    )


def test_level_tallies_count_visible_and_hidden_cases_per_level():
    statuses = {"ex1": CaseStatus.PASS, "h1": CaseStatus.PASS, "h2": CaseStatus.FAIL}
    judged = Judgement(
        5,
        tuple(
            verdict(graded, statuses.get(graded.id, CaseStatus.PASS))
            for graded in CASES
            if graded.id != "h3"
        ),
    )
    assert level_tallies(CASES, judged) == (LevelTally(1, 1, 1, 2, 1), LevelTally(2, 1, 1, 1, 0))


def test_code_that_did_not_load_passes_no_case_of_any_level():
    judged = Judgement(5, load_error=UserError("SymbolNotFound", "bank.bank has no class Bank"))
    assert level_tallies(CASES, judged) == (LevelTally(1, 1, 0, 2, 0), LevelTally(2, 1, 0, 1, 0))


def test_a_level_tally_adds_visible_and_hidden_cases():
    assert (LevelTally(2, 2, 1, 3, 2).total, LevelTally(2, 2, 1, 3, 2).passed) == (5, 3)


def test_a_level_tally_counts_its_failing_hidden_cases():
    assert LevelTally(2, 2, 2, 3, 1).hidden_failed == 2


@pytest.mark.parametrize(
    ("levels", "finished"),
    [
        ((tally(1, 1), tally(2, 2)), 0),
        ((tally(1, 2), tally(2, 1)), 1),
        ((tally(1, 2), tally(2, 2)), 2),
        ((tally(1, 1), tally(2, 2), tally(3, 2)), 0),
    ],
)
def test_levels_finished_stop_at_the_first_level_that_did_not_pass(levels, finished):
    assert submission(*levels).levels_finished == finished


def test_no_counted_submission_finishes_no_level():
    assert levels_finished(None) == 0


def test_the_counted_submission_is_the_latest_that_graded_every_unlocked_level():
    every_level = submission(tally(1, 2), minutes=1)
    lower_level = submission(tally(1, 1), every_level=False, minutes=2)
    assert counted_submission([submission(tally(1, 1)), every_level, lower_level]) == every_level


def test_submissions_of_lower_levels_alone_count_for_nothing():
    assert counted_submission([submission(tally(1, 2), every_level=False)]) is None


@pytest.mark.parametrize(
    ("finished", "cap"),
    [(4, None), (3, Grade.HARD), (2, Grade.AGAIN), (1, Grade.AGAIN), (0, Grade.AGAIN)],
)
def test_the_levels_finished_cap_the_grade(finished, cap):
    assert level_grade_cap(finished, 4) == cap


def test_the_best_per_level_keeps_the_most_passed_cases_of_each_level():
    first = submission(tally(1, 2), tally(2, 1))
    second = submission(tally(1, 1), tally(2, 2), tally(3, 0))
    assert best_per_level([first, second]) == (tally(1, 2), tally(2, 2), tally(3, 0))
