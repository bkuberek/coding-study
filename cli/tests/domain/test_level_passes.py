"""Level passes: a pass through level N of M (docs/decisions/0024-level-passes.md,
docs/specs/progress-and-scheduling.md#level-passes)."""

from datetime import UTC, datetime, timedelta

import pytest

from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus, Grade
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected, OperationSequence
from coding_study.domain.judging import CaseVerdict, Judgement, RunnableCase
from coding_study.domain.level_passes import (
    LevelMastery,
    LevelsPassed,
    judged_levels,
    level_mastery,
    level_outcome,
    recorded_levels,
)
from coding_study.domain.problem import Language, ProblemKind
from coding_study.domain.runs import Returned

STARTED = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
OPS = OperationSequence(("Store",), ((),))
CASES = (
    Case("ex1", OPS, Expected([None]), visible=True, level=1),
    Case("h1", OPS, Expected([None]), level=1),
    Case("ex2", OPS, Expected([None]), visible=True, level=2),
    Case("h2", OPS, Expected([None]), level=2),
    Case("ex3", OPS, Expected([None]), visible=True, level=3),
)
NEW = AttemptMode.NEW
MOCK = AttemptMode.MOCK
PROGRESSIVE = ProblemKind.PROGRESSIVE
PROJECT = ProblemKind.PROJECT


def judgement(**statuses: CaseStatus) -> Judgement:
    """A verdict for each case named, in CASES order; the others did not run."""
    verdicts = tuple(
        CaseVerdict(
            RunnableCase(case.id, OPS, case.expected, visible=case.visible),
            statuses[case.id],
            Returned([None], 1000),
        )
        for case in CASES
        if case.id in statuses
    )
    return Judgement(len(verdicts), verdicts)


PASS = CaseStatus.PASS
FAIL = CaseStatus.FAIL


def attempt(
    status: AttemptStatus,
    levels: tuple[int, int] | None = None,
    hours: int = 0,
    language: Language = Language.PYTHON,
) -> Attempt:
    passed, total = levels if levels else (None, None)
    return Attempt(
        id=hours + 1,
        slug="level-store",
        language=language,
        mode=NEW,
        status=status,
        started_at=STARTED + timedelta(hours=hours),
        ended_at=STARTED + timedelta(hours=hours, minutes=30),
        levels_passed=passed,
        levels_total=total,
    )


PASSED = AttemptStatus.PASSED
FAILED = AttemptStatus.FAILED


# The levels a run passed


def test_a_run_that_passed_every_case_passed_every_level():
    assert judged_levels(CASES, judgement(ex1=PASS, h1=PASS, ex2=PASS, h2=PASS, ex3=PASS)) == 3


def test_a_run_passes_the_levels_below_its_first_failing_case():
    assert judged_levels(CASES, judgement(ex1=PASS, h1=PASS, ex2=PASS, h2=FAIL, ex3=PASS)) == 1


def test_a_failing_case_of_level_1_passes_no_level():
    assert judged_levels(CASES, judgement(ex1=FAIL, h1=PASS, ex2=PASS, h2=PASS)) == 0


def test_a_level_whose_cases_did_not_all_run_is_not_passed():
    assert judged_levels(CASES, judgement(ex1=PASS, h1=PASS, ex2=PASS)) == 1


def test_a_run_of_the_unlocked_levels_passes_them():
    assert judged_levels(CASES, judgement(ex1=PASS, h1=PASS, ex2=PASS, h2=PASS)) == 2


def test_code_that_did_not_build_passes_no_level():
    assert judged_levels(CASES, None) == 0


# What `cstudy done` does with the levels passed


@pytest.mark.parametrize("kind", [PROGRESSIVE, PROJECT])
def test_a_pass_through_a_level_below_the_last_is_a_pass_without_a_cap(kind):
    outcome = level_outcome(LevelsPassed(2, 4), NEW, kind)
    assert (outcome.rating_needed, outcome.passes, outcome.cap) == (True, True, None)


@pytest.mark.parametrize("kind", [PROGRESSIVE, PROJECT])
def test_no_level_passed_needs_gave_up_and_fails(kind):
    outcome = level_outcome(LevelsPassed(0, 4), NEW, kind)
    assert (outcome.rating_needed, outcome.passes) == (False, False)


@pytest.mark.parametrize("kind", [PROGRESSIVE, PROJECT])
def test_every_level_is_a_pass_in_any_mode(kind):
    outcome = level_outcome(LevelsPassed(4, 4), MOCK, kind)
    assert (outcome.rating_needed, outcome.passes, outcome.cap) == (True, True, None)


def test_a_progressive_mock_needs_every_level_for_a_rating():
    outcome = level_outcome(LevelsPassed(3, 4), MOCK, PROGRESSIVE)
    assert (outcome.rating_needed, outcome.passes) == (False, False)


@pytest.mark.parametrize(("passed", "cap"), [(3, Grade.HARD), (2, Grade.AGAIN), (1, Grade.AGAIN)])
def test_a_project_mock_keeps_the_level_cap_and_fails(passed, cap):
    outcome = level_outcome(LevelsPassed(passed, 4), MOCK, PROJECT)
    assert (outcome.rating_needed, outcome.passes, outcome.cap) == (True, False, cap)


@pytest.mark.parametrize(
    ("levels", "text"),
    [(LevelsPassed(2, 4), "through level 2 of 4"), (LevelsPassed(1, 1), "through level 1 of 1")],
)
def test_the_levels_read_as_through_level_n_of_m(levels, text):
    assert levels.text == text


@pytest.mark.parametrize(
    ("levels", "partial"),
    [(LevelsPassed(0, 4), False), (LevelsPassed(2, 4), True), (LevelsPassed(4, 4), False)],
)
def test_a_partial_pass_passed_a_level_but_not_the_last(levels, partial):
    assert levels.partial is partial


# What an attempt recorded


def test_a_finished_attempt_reads_the_levels_it_recorded():
    assert recorded_levels(attempt(PASSED, (2, 4)), 4) == LevelsPassed(2, 4)


def test_an_attempt_passed_before_level_passes_passed_every_level():
    assert recorded_levels(attempt(PASSED), 4) == LevelsPassed(4, 4)


def test_an_attempt_failed_before_level_passes_recorded_no_levels():
    assert recorded_levels(attempt(FAILED), 4) is None


def test_an_attempt_in_progress_recorded_no_levels():
    assert recorded_levels(attempt(AttemptStatus.IN_PROGRESS), 4) is None


# Mastery and the next goal


def test_without_finished_attempts_there_is_no_mastery_or_goal():
    assert level_mastery((), 4) == LevelMastery(4, None, None)


def test_the_best_is_the_most_levels_a_passed_attempt_passed():
    attempts = (attempt(PASSED, (2, 4), hours=2), attempt(PASSED, (3, 4), hours=1))
    assert level_mastery(attempts, 4).best == 3


def test_a_failed_attempt_is_never_the_best():
    attempts = (attempt(FAILED, (3, 4), hours=2), attempt(PASSED, (1, 4), hours=1))
    assert level_mastery(attempts, 4).best == 1


def test_last_time_is_the_latest_attempt_that_passed_a_level():
    attempts = (
        attempt(FAILED, (0, 4), hours=3),
        attempt(PASSED, (2, 4), hours=2),
        attempt(PASSED, (3, 4), hours=1),
    )
    assert level_mastery(attempts, 4).last_time == 2


def test_the_goal_is_the_level_after_last_time():
    mastery = level_mastery((attempt(PASSED, (2, 4)),), 4)
    assert (mastery.try_level, mastery.goal) == (3, "last time: through level 2 of 4; try level 3")


def test_every_level_passed_last_time_sets_no_goal():
    mastery = level_mastery((attempt(PASSED, (4, 4)),), 4)
    assert (mastery.try_level, mastery.goal) == (None, None)


def test_an_old_pass_counts_every_level():
    assert level_mastery((attempt(PASSED),), 4) == LevelMastery(4, 4, 4)


def test_a_problem_that_gained_a_level_is_mastered_up_to_the_levels_passed():
    mastery = level_mastery((attempt(PASSED, (3, 3)),), 4)
    assert (mastery.best, mastery.try_level) == (3, 4)

