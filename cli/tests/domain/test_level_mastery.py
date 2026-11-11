"""Mastery per level: the recall test of the problem status, applied to each level reached
(docs/decisions/0024-level-passes.md#mastery-per-level,
docs/specs/progress-and-scheduling.md#mastery-per-level)."""

from datetime import UTC, date, datetime

import pytest

from coding_study.domain.attempts import AttemptStatus, Grade
from coding_study.domain.config import ScheduleSettings
from coding_study.domain.level_passes import (
    LevelsPassed,
    next_level_reviews,
    status_cell,
    status_text,
)
from coding_study.domain.scheduling import (
    LevelReview,
    ProblemProgress,
    ProblemStatus,
    ReviewState,
    ScheduleEntry,
    next_review_state,
)

SETTINGS = ScheduleSettings()
UPDATED = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
DUE = date(2026, 12, 1)
PASSED = frozenset({AttemptStatus.PASSED})
OK = Grade.OK
MASTERED_STATE = ReviewState(interval_days=45, reps=4)
LEARNING_STATE = ReviewState(interval_days=3, reps=1)


def entry(state: ReviewState, levels: tuple[LevelReview, ...] | None) -> ScheduleEntry:
    return ScheduleEntry("level-store", state, DUE, OK, UPDATED, levels)


def done(
    previous: ScheduleEntry | None, passed: int, last: int, grade: Grade = OK
) -> ScheduleEntry:
    """The schedule after a graded attempt through level `passed` of `last`, as `cstudy done`
    leaves it."""
    state = next_review_state(
        previous.state if previous else ReviewState(), grade, SETTINGS.max_interval_days
    )
    levels = next_level_reviews(previous, LevelsPassed(passed, last), grade, SETTINGS)
    return ScheduleEntry("level-store", state, DUE, grade, UPDATED, levels)


def mastered(schedule: ScheduleEntry, last: int) -> int:
    return ProblemProgress(PASSED, schedule).mastered_levels(last)


# What a graded attempt does to each level


def test_a_first_pass_through_level_2_gives_level_2_its_own_review():
    assert done(None, 2, 4).levels == (
        LevelReview(2, next_review_state(ReviewState(), OK, SETTINGS.max_interval_days), OK),
    )


def test_a_level_reached_before_and_not_passed_now_lapses():
    before = done(None, 2, 4)
    assert before.levels is not None
    lapsed = next_review_state(before.levels[0].state, Grade.AGAIN, SETTINGS.max_interval_days)
    assert done(before, 1, 4).levels == (LevelReview(2, lapsed, Grade.AGAIN),)


def test_a_level_never_reached_has_no_review():
    assert [review.level for review in done(done(None, 3, 4), 2, 4).levels or ()] == [2, 3]


def test_a_schedule_from_before_level_passes_starts_every_level_from_its_own_state():
    legacy = entry(MASTERED_STATE, None)
    expected = next_review_state(MASTERED_STATE, OK, SETTINGS.max_interval_days)
    assert done(legacy, 4, 4).levels == tuple(
        LevelReview(level, expected, OK) for level in (2, 3, 4)
    )


# How many levels are mastered


def test_a_problem_not_mastered_has_no_level_mastered():
    assert mastered(entry(LEARNING_STATE, ()), 4) == 0


def test_a_schedule_from_before_level_passes_masters_every_level():
    assert mastered(entry(MASTERED_STATE, None), 4) == 4


def test_level_1_follows_the_problems_own_review():
    assert mastered(entry(MASTERED_STATE, ()), 4) == 1


def test_each_level_after_the_first_needs_its_own_recall():
    levels = (LevelReview(2, MASTERED_STATE, OK), LevelReview(3, LEARNING_STATE, OK))
    assert mastered(entry(MASTERED_STATE, levels), 4) == 2


def test_a_level_whose_last_grade_was_hard_is_not_mastered():
    levels = (LevelReview(2, MASTERED_STATE, Grade.HARD),)
    assert mastered(entry(MASTERED_STATE, levels), 4) == 1


def test_every_level_recalled_masters_the_problem():
    levels = tuple(LevelReview(level, MASTERED_STATE, OK) for level in (2, 3))
    assert mastered(entry(MASTERED_STATE, levels), 3) == 3


def test_the_configured_threshold_applies_to_each_level():
    levels = (LevelReview(2, ReviewState(interval_days=10, reps=3), OK),)
    progress = ProblemProgress(
        PASSED, entry(ReviewState(interval_days=10, reps=3), levels), mastered_interval_days=10
    )
    assert progress.mastered_levels(2) == 2


# The worked example of the ADR: climbing to a level does not inherit mastery


def reviews(previous: ScheduleEntry | None, passed: int, count: int) -> ScheduleEntry:
    schedule = previous
    for _ in range(count):
        schedule = done(schedule, passed, 4)
    assert schedule is not None
    return schedule


def test_four_reviews_through_level_2_master_it():
    assert mastered(reviews(None, 2, 4), 4) == 2


def test_one_pass_through_level_3_after_mastering_level_2_keeps_mastery_at_2():
    assert mastered(reviews(reviews(None, 2, 4), 3, 1), 4) == 2


def test_level_3_is_mastered_once_its_own_reviews_reach_the_interval():
    assert mastered(reviews(reviews(None, 2, 4), 3, 4), 4) == 3


# How the status reads


@pytest.mark.parametrize(
    ("status", "levels", "text"),
    [
        (ProblemStatus.MASTERED, (2, 4), "mastered through level 2 of 4"),
        (ProblemStatus.MASTERED, (4, 4), "mastered"),
        (ProblemStatus.MASTERED, None, "mastered"),
        (ProblemStatus.PASSED, (0, 4), "passed"),
        (ProblemStatus.IN_PROGRESS, (2, 4), "in progress"),
    ],
)
def test_a_problem_mastered_below_its_last_level_says_through_which(status, levels, text):
    assert status_text(status, levels) == text


def test_a_narrow_column_writes_the_levels_as_a_fraction():
    assert status_cell(ProblemStatus.MASTERED, (2, 4)) == "mastered 2/4"
