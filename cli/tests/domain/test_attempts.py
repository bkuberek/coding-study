from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from coding_study.domain.attempts import (
    Attempt,
    AttemptMode,
    AttemptStatus,
    Grade,
    GradeCap,
    Rating,
    attempt_caps,
    cap_grade,
    capped_by,
    grade_attempt,
    parse_timer,
)
from coding_study.domain.problem import Language

STARTED = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
ATTEMPT = Attempt(
    id=1,
    slug="two-sum",
    language=Language.PYTHON,
    mode=AttemptMode.NEW,
    status=AttemptStatus.IN_PROGRESS,
    started_at=STARTED,
    first_pass_at=STARTED + timedelta(minutes=10),
)
ENDED = STARTED + timedelta(minutes=18, seconds=40)


@pytest.mark.parametrize(
    ("rating", "grade"),
    [(Rating.EASY, Grade.EASY), (Rating.OK, Grade.OK), (Rating.HARD, Grade.HARD)],
)
def test_rating_sets_the_grade(rating, grade):
    assert grade_attempt(ATTEMPT, rating, ENDED) is grade


def test_giving_up_grades_again():
    assert grade_attempt(ATTEMPT, None, ENDED) is Grade.AGAIN


def test_revealing_the_solution_before_a_full_pass_grades_again():
    attempt = replace(ATTEMPT, solution_revealed=True, first_pass_at=None)
    assert grade_attempt(attempt, Rating.EASY, ENDED) is Grade.AGAIN


def test_a_hint_caps_the_grade_at_ok():
    assert grade_attempt(replace(ATTEMPT, hints_used=1), Rating.EASY, ENDED) is Grade.OK


def test_a_hint_keeps_a_lower_grade():
    assert grade_attempt(replace(ATTEMPT, hints_used=2), Rating.HARD, ENDED) is Grade.HARD


def test_finishing_over_the_timer_caps_the_grade_at_hard():
    attempt = replace(ATTEMPT, time_limit_s=15 * 60)
    assert grade_attempt(attempt, Rating.EASY, ENDED) is Grade.HARD


def test_finishing_exactly_at_the_timer_is_not_over_time():
    attempt = replace(ATTEMPT, time_limit_s=int((ENDED - STARTED).total_seconds()))
    assert grade_attempt(attempt, Rating.EASY, ENDED) is Grade.EASY


def test_the_lowest_cap_wins():
    assert cap_grade(Grade.EASY, (Grade.OK, Grade.HARD)) is Grade.HARD


def test_caps_never_raise_a_grade():
    assert cap_grade(Grade.AGAIN, (Grade.OK,)) is Grade.AGAIN


def test_no_caps_keep_the_grade():
    assert cap_grade(Grade.EASY, ()) is Grade.EASY


def test_an_attempt_without_hints_reveals_or_a_time_box_has_no_caps():
    assert attempt_caps(ATTEMPT, ENDED) == {}


def test_a_hint_is_a_cap_at_ok():
    assert attempt_caps(replace(ATTEMPT, hints_used=1), ENDED) == {GradeCap.HINT: Grade.OK}


def test_finishing_past_the_time_box_is_a_cap_at_hard():
    attempt = replace(ATTEMPT, time_limit_s=15 * 60)
    assert attempt_caps(attempt, ENDED) == {GradeCap.TIME_BOX: Grade.HARD}


def test_a_solution_revealed_before_a_full_pass_is_a_cap_at_again():
    attempt = replace(ATTEMPT, solution_revealed=True, first_pass_at=None)
    assert attempt_caps(attempt, ENDED) == {GradeCap.SOLUTION: Grade.AGAIN}


def test_a_solution_revealed_after_a_full_pass_is_no_cap():
    assert attempt_caps(replace(ATTEMPT, solution_revealed=True), ENDED) == {}


def test_a_cap_below_the_rating_applied():
    assert capped_by(Rating.EASY, {GradeCap.HINT: Grade.OK}) == (GradeCap.HINT,)


def test_a_cap_at_the_rating_did_not_apply():
    assert capped_by(Rating.OK, {GradeCap.HINT: Grade.OK}) == ()


def test_no_cap_applies_without_a_rating():
    assert capped_by(None, {GradeCap.SOLUTION: Grade.AGAIN}) == ()


def test_applied_caps_follow_the_cap_order():
    caps = {GradeCap.LEVELS: Grade.HARD, GradeCap.HINT: Grade.OK, GradeCap.TIME_BOX: Grade.HARD}
    assert capped_by(Rating.EASY, caps) == (GradeCap.HINT, GradeCap.TIME_BOX, GradeCap.LEVELS)


def test_solve_time_is_wall_clock_since_start():
    assert ATTEMPT.solve_time(ENDED) == timedelta(minutes=18, seconds=40)


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("25m", 1500), ("1h", 3600), ("90s", 90), ("1h30m", 5400), ("45", 2700)],
)
def test_timer_durations(text, seconds):
    assert parse_timer(text) == seconds


@pytest.mark.parametrize("text", ["", "0m", "m", "25x", "-5m", "1.5h"])
def test_invalid_timer_durations(text):
    with pytest.raises(ValueError, match="invalid timer"):
        parse_timer(text)


def test_an_abandoned_attempt_is_over_at_the_moment_it_was_abandoned():
    ended = ATTEMPT.abandoned(ENDED)
    assert (ended.status, ended.ended_at) == (AttemptStatus.ABANDONED, ENDED)


def test_abandoning_changes_nothing_but_the_status_and_the_end():
    ended = ATTEMPT.abandoned(ENDED)
    assert replace(ended, status=ATTEMPT.status, ended_at=None) == ATTEMPT
