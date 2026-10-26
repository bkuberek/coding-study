from datetime import UTC, date, datetime, timedelta
from fractions import Fraction

import pytest

from coding_study.domain.attempts import Grade
from coding_study.domain.problem import Track
from coding_study.domain.weakness import GradedAttempt, Group, GroupHistory, group_of

TODAY = date(2026, 10, 24)


def graded(grade: Grade, days_ago: int = 0, attempt_id: int = 1) -> GradedAttempt:
    ended_on = TODAY - timedelta(days=days_ago)
    ended_at = datetime(ended_on.year, ended_on.month, ended_on.day, 12, tzinfo=UTC)
    return GradedAttempt(attempt_id, "two-sum", grade, ended_at, ended_on)


def weakness(*attempts: GradedAttempt, problems: int = 3, mastered: int = 0) -> Fraction:
    return GroupHistory(problems, mastered, attempts).weakness(TODAY)


def test_an_untouched_group_scores_three_quarters():
    assert weakness() == Fraction(3, 4)


@pytest.mark.parametrize("grade", [Grade.OK, Grade.EASY])
def test_one_passed_attempt_drops_the_group_to_three_tenths(grade):
    assert weakness(graded(grade)) == Fraction(3, 10)


@pytest.mark.parametrize("grade", [Grade.AGAIN, Grade.HARD])
def test_one_failed_attempt_raises_the_group_to_four_fifths(grade):
    assert weakness(graded(grade)) == Fraction(4, 5)


def test_fail_rate_counts_only_the_last_ten_attempts():
    old_failures = [graded(Grade.AGAIN, 40 + index, attempt_id=index) for index in range(5)]
    recent_passes = [graded(Grade.OK, attempt_id=100 + index) for index in range(10)]
    assert weakness(*old_failures, *recent_passes) == Fraction(3, 10)


def test_fail_rate_is_the_share_of_low_grades():
    attempts = (graded(Grade.HARD, attempt_id=1), graded(Grade.EASY, attempt_id=2))
    assert weakness(*attempts) == Fraction(1, 2) * Fraction(1, 2) + Fraction(3, 10)


def test_mastered_problems_lower_the_score():
    assert weakness(graded(Grade.OK), problems=4, mastered=2) == Fraction(3, 10) * Fraction(1, 2)


def test_staleness_grows_with_the_days_since_the_last_attempt():
    assert weakness(graded(Grade.OK, days_ago=15)) == Fraction(3, 10) + Fraction(1, 5) / 2


def test_staleness_stops_growing_after_thirty_days():
    assert weakness(graded(Grade.OK, days_ago=300)) == Fraction(1, 2)


def test_staleness_uses_the_latest_attempt():
    attempts = (graded(Grade.OK, days_ago=60, attempt_id=1), graded(Grade.OK, attempt_id=2))
    assert weakness(*attempts) == Fraction(3, 10)


def test_a_group_without_problems_has_no_mastery():
    assert weakness(problems=0) == Fraction(3, 4)


def test_the_group_of_a_dsa_problem_is_its_primary_pattern():
    assert group_of(Track.DSA, ("sliding-window", "monotonic-stack")).name == "sliding-window"


def test_the_group_of_another_track_is_the_track():
    assert group_of(Track.PRACTICAL, ("arrays-hashing",)) == Group(Track.PRACTICAL)


def test_a_dsa_problem_without_patterns_groups_by_track():
    assert group_of(Track.DSA, ()).name == "dsa"


def test_pattern_groups_follow_the_taxonomy_order():
    groups = [group_of(Track.DSA, ("stack",)), group_of(Track.DSA, ("arrays-hashing",))]
    assert sorted(groups, key=Group.tie_break_key)[0].name == "arrays-hashing"


def test_pattern_groups_come_before_track_groups():
    groups = [Group(Track.LLD), group_of(Track.DSA, ("segment-tree-fenwick",))]
    assert sorted(groups, key=Group.tie_break_key)[0].name == "segment-tree-fenwick"


def test_track_groups_follow_the_track_order():
    groups = [Group(Track.LLD), Group(Track.PRACTICAL)]
    assert sorted(groups, key=Group.tie_break_key)[0].name == "practical"
