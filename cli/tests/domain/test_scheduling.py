from datetime import UTC, date, datetime

import pytest

from coding_study.domain.attempts import AttemptStatus, Grade
from coding_study.domain.scheduling import (
    ProblemProgress,
    ProblemStatus,
    ReviewState,
    ScheduleEntry,
    next_review_state,
)

MAX_INTERVAL = 180
TODAY = date(2026, 10, 24)


def replay(*grades: Grade) -> list[ReviewState]:
    states, state = [], ReviewState()
    for grade in grades:
        state = next_review_state(state, grade, MAX_INTERVAL)
        states.append(state)
    return states


def test_worked_sequence_intervals():
    states = replay(Grade.OK, Grade.OK, Grade.OK, Grade.HARD, Grade.AGAIN, Grade.OK)
    assert [state.interval_days for state in states] == [3, 7, 18, 22, 1, 3]


def test_worked_sequence_ease():
    states = replay(Grade.OK, Grade.OK, Grade.OK, Grade.HARD, Grade.AGAIN, Grade.OK)
    assert [state.ease for state in states] == [2.5, 2.5, 2.5, 2.35, 2.15, 2.15]


def test_worked_sequence_reps():
    states = replay(Grade.OK, Grade.OK, Grade.OK, Grade.HARD, Grade.AGAIN, Grade.OK)
    assert [state.reps for state in states] == [1, 2, 3, 4, 0, 1]


def test_again_counts_a_lapse():
    assert replay(Grade.OK, Grade.AGAIN)[-1].lapses == 1


@pytest.mark.parametrize(
    ("grade", "interval"), [(Grade.AGAIN, 1), (Grade.HARD, 2), (Grade.OK, 3), (Grade.EASY, 5)]
)
def test_first_review_intervals(grade, interval):
    assert next_review_state(ReviewState(), grade, MAX_INTERVAL).interval_days == interval


@pytest.mark.parametrize(("grade", "interval"), [(Grade.OK, 7), (Grade.EASY, 12)])
def test_second_review_intervals(grade, interval):
    state = ReviewState(reps=1, interval_days=3)
    assert next_review_state(state, grade, MAX_INTERVAL).interval_days == interval


def test_easy_later_reviews_grow_by_ease_and_bonus():
    state = ReviewState(reps=2, interval_days=10, ease=2.5)
    assert next_review_state(state, Grade.EASY, MAX_INTERVAL).interval_days == 33


def test_easy_raises_ease_up_to_the_maximum():
    state = ReviewState(ease=2.95)
    assert next_review_state(state, Grade.EASY, MAX_INTERVAL).ease == 3.0


def test_ease_never_drops_below_the_minimum():
    state = ReviewState(ease=1.4)
    assert next_review_state(state, Grade.AGAIN, MAX_INTERVAL).ease == 1.3


def test_hard_grows_the_interval_by_at_least_one_day():
    state = ReviewState(reps=3, interval_days=2)
    assert next_review_state(state, Grade.HARD, MAX_INTERVAL).interval_days == 3


def test_intervals_are_capped():
    state = ReviewState(reps=5, interval_days=100, ease=2.5)
    assert next_review_state(state, Grade.OK, 180).interval_days == 180


def schedule(due_on: date, interval: int = 3, grade: Grade = Grade.OK) -> ScheduleEntry:
    state = ReviewState(interval_days=interval, reps=1)
    return ScheduleEntry("two-sum", state, due_on, grade, datetime(2026, 10, 1, tzinfo=UTC))


def test_untouched_problem_is_new():
    assert ProblemProgress().status(TODAY) is ProblemStatus.NEW


def test_abandoned_and_unfinished_attempts_keep_a_problem_new():
    progress = ProblemProgress(frozenset({AttemptStatus.ABANDONED, AttemptStatus.IN_PROGRESS}))
    assert progress.status(TODAY) is ProblemStatus.NEW


def test_only_failed_attempts_is_attempted():
    progress = ProblemProgress(frozenset({AttemptStatus.FAILED}), schedule(date(2026, 11, 1)))
    assert progress.status(TODAY) is ProblemStatus.ATTEMPTED


def test_a_passed_attempt_is_passed():
    progress = ProblemProgress(frozenset({AttemptStatus.PASSED}), schedule(date(2026, 11, 1)))
    assert progress.status(TODAY) is ProblemStatus.PASSED


def test_long_interval_with_a_good_grade_is_mastered():
    entry = schedule(date(2026, 11, 30), interval=21)
    progress = ProblemProgress(frozenset({AttemptStatus.PASSED}), entry)
    assert progress.status(TODAY) is ProblemStatus.MASTERED


def test_long_interval_after_a_hard_grade_is_not_mastered():
    entry = schedule(date(2026, 11, 30), interval=30, grade=Grade.HARD)
    progress = ProblemProgress(frozenset({AttemptStatus.PASSED}), entry)
    assert progress.status(TODAY) is ProblemStatus.PASSED


@pytest.mark.parametrize("due_on", [TODAY, date(2026, 10, 1)])
def test_due_review_shows_instead_of_passed(due_on):
    progress = ProblemProgress(frozenset({AttemptStatus.PASSED}), schedule(due_on, interval=30))
    assert progress.status(TODAY) is ProblemStatus.DUE
