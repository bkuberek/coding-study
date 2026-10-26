from datetime import UTC, date, datetime, timedelta
from fractions import Fraction

import pytest

from coding_study.domain.attempts import AttemptStatus, Grade
from coding_study.domain.bench_verdict import Verdict
from coding_study.domain.next_selection import Candidate
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.progress_stats import (
    BenchGrade,
    StatsAttempt,
    StatsGrouping,
    StatsQuery,
    progress_stats,
    streak_days,
)
from coding_study.domain.scheduling import ProblemProgress, ReviewState, ScheduleEntry

TODAY = date(2026, 10, 24)
PASSED = ProblemProgress(frozenset({AttemptStatus.PASSED}))


def problem(slug: str, **fields: object) -> Candidate:
    defaults: dict[str, object] = {"difficulty": Difficulty.EASY, "patterns": ("arrays-hashing",)}
    defaults.update(fields)
    return Candidate("0001", slug, Track(defaults.pop("track", Track.DSA)), **defaults)  # type: ignore[arg-type]


def item(slug: str, **fields: object) -> Candidate:
    defaults: dict[str, object] = {"difficulty": Difficulty.MEDIUM, "languages": ()}
    defaults.update(fields)
    return Candidate(None, slug, Track.SYSTEM_DESIGN, **defaults)  # type: ignore[arg-type]


def mastered(due_in_days: int = 10) -> ProblemProgress:
    entry = ScheduleEntry(
        "any",
        ReviewState(interval_days=21, reps=3),
        TODAY + timedelta(days=due_in_days),
        Grade.OK,
        datetime(2026, 10, 1, tzinfo=UTC),
    )
    return ProblemProgress(frozenset({AttemptStatus.PASSED}), entry)


def due(in_days: int) -> ProblemProgress:
    entry = ScheduleEntry(
        "any",
        ReviewState(interval_days=3, reps=1),
        TODAY + timedelta(days=in_days),
        Grade.OK,
        datetime(2026, 10, 1, tzinfo=UTC),
    )
    return ProblemProgress(frozenset({AttemptStatus.PASSED}), entry)


def attempt(
    slug: str,
    days_ago: int = 0,
    attempt_id: int = 1,
    minutes: int = 10,
    passed: bool = True,
    language: Language | None = Language.PYTHON,
) -> StatsAttempt:
    ended_on = TODAY - timedelta(days=days_ago)
    ended_at = datetime(ended_on.year, ended_on.month, ended_on.day, 12, tzinfo=UTC)
    return StatsAttempt(
        id=attempt_id,
        slug=slug,
        language=language,
        passed=passed,
        grade=Grade.OK if passed else Grade.AGAIN,
        started_at=ended_at - timedelta(minutes=minutes),
        ended_at=ended_at,
        ended_on=ended_on,
    )


def stats(entries, attempts=(), bench=(), **query: object):
    return progress_stats(entries, attempts, bench, StatsQuery(TODAY, **query))  # type: ignore[arg-type]


def group(result, name: str):
    return next(found for found in result.groups if found.name == name)


def test_groups_follow_the_taxonomy_order():
    entries = [problem("a", patterns=("stack",)), problem("b", patterns=("two-pointers",))]
    assert [found.name for found in stats(entries).groups] == ["two-pointers", "stack"]


def test_track_groups_come_after_pattern_groups():
    entries = [item("design"), problem("a")]
    assert [found.name for found in stats(entries).groups] == ["arrays-hashing", "system-design"]


def test_draft_content_is_left_out():
    entries = [problem("a"), problem("b", content=ContentStatus.DRAFT)]
    assert group(stats(entries), "arrays-hashing").problems == 1


def test_attempted_counts_problems_with_a_finished_attempt():
    entries = [problem("a"), problem("b"), problem("c")]
    attempts = [attempt("a", attempt_id=1), attempt("a", attempt_id=2), attempt("b", attempt_id=3)]
    assert group(stats(entries, attempts), "arrays-hashing").attempted == 2


def test_passed_counts_problems_with_a_passed_attempt():
    attempts = [attempt("a", attempt_id=1), attempt("b", attempt_id=2, passed=False)]
    assert group(stats([problem("a"), problem("b")], attempts), "arrays-hashing").passed == 1


def test_mastered_counts_mastered_problems():
    entries = [problem("a", progress=mastered()), problem("b", progress=PASSED)]
    assert group(stats(entries), "arrays-hashing").mastered == 1


def test_pass_rate_covers_the_last_ten_attempts():
    failures = [attempt("a", 20 + index, index, passed=False) for index in range(5)]
    passes = [attempt("a", index, 100 + index) for index in range(10)]
    found = group(stats([problem("a")], [*failures, *passes]), "arrays-hashing")
    assert (found.recent_passed, found.recent_attempts) == (10, 10)


def test_pass_rate_is_the_passed_share():
    attempts = [attempt("a", attempt_id=1), attempt("a", attempt_id=2, passed=False)]
    assert group(stats([problem("a")], attempts), "arrays-hashing").pass_rate == Fraction(1, 2)


def test_pass_rate_without_attempts_is_none():
    assert group(stats([problem("a")]), "arrays-hashing").pass_rate is None


def test_median_solve_time_uses_passed_attempts_only():
    attempts = [
        attempt("a", attempt_id=1, minutes=10),
        attempt("a", attempt_id=2, minutes=30),
        attempt("a", attempt_id=3, minutes=90, passed=False),
    ]
    found = group(stats([problem("a")], attempts), "arrays-hashing")
    assert found.median_solve == timedelta(minutes=20)


def test_median_solve_time_without_passes_is_none():
    attempts = [attempt("a", passed=False)]
    assert group(stats([problem("a")], attempts), "arrays-hashing").median_solve is None


def test_weakness_matches_the_next_selection_score():
    assert group(stats([problem("a")]), "arrays-hashing").weakness == Fraction(3, 4)


def test_weakness_after_one_pass():
    assert group(stats([problem("a")], [attempt("a")]), "arrays-hashing").weakness == Fraction(
        3, 10
    )


def test_by_track_groups_every_dsa_pattern_together():
    entries = [problem("a"), problem("b", patterns=("stack",)), item("design")]
    result = stats(entries, grouping=StatsGrouping.TRACK)
    assert [(found.name, found.problems) for found in result.groups] == [
        ("dsa", 2),
        ("system-design", 1),
    ]


def test_by_difficulty_orders_easy_to_hard():
    entries = [problem("a", difficulty=Difficulty.HARD), problem("b")]
    result = stats(entries, grouping=StatsGrouping.DIFFICULTY)
    assert [found.name for found in result.groups] == ["easy", "hard"]


def test_by_language_counts_problems_offered_in_it():
    entries = [problem("a"), problem("b", languages=(Language.PYTHON,))]
    result = stats(entries, grouping=StatsGrouping.LANG)
    assert [(found.name, found.problems) for found in result.groups] == [
        ("python", 2),
        ("typescript", 1),
        ("java", 1),
        ("kotlin", 1),
    ]


def test_by_language_leaves_items_out():
    result = stats([item("design")], grouping=StatsGrouping.LANG)
    assert result.groups == ()


def test_by_language_counts_attempts_in_that_language():
    attempts = [attempt("a", attempt_id=1, language=Language.KOTLIN)]
    result = stats([problem("a")], attempts, grouping=StatsGrouping.LANG)
    assert [(found.name, found.attempted) for found in result.groups] == [
        ("python", 0),
        ("typescript", 0),
        ("java", 0),
        ("kotlin", 1),
    ]


def test_by_language_counts_mastery_where_the_problem_was_passed():
    entries = [problem("a", progress=mastered())]
    attempts = [attempt("a", language=Language.JAVA)]
    result = stats(entries, attempts, grouping=StatsGrouping.LANG)
    assert {found.name: found.mastered for found in result.groups}["java"] == 1


def test_by_language_mastery_elsewhere_does_not_count():
    entries = [problem("a", progress=mastered())]
    attempts = [attempt("a", language=Language.JAVA)]
    result = stats(entries, attempts, grouping=StatsGrouping.LANG)
    assert {found.name: found.mastered for found in result.groups}["python"] == 0


def test_by_language_mastery_needs_a_pass_in_the_language():
    entries = [problem("a", progress=mastered())]
    attempts = [attempt("a", language=Language.JAVA, passed=False)]
    result = stats(entries, attempts, grouping=StatsGrouping.LANG)
    assert {found.name: found.mastered for found in result.groups}["java"] == 0


def test_since_drops_earlier_attempts_from_the_attempt_columns():
    attempts = [attempt("a", days_ago=10, attempt_id=1), attempt("b", days_ago=1, attempt_id=2)]
    result = stats([problem("a"), problem("b")], attempts, since=TODAY - timedelta(days=5))
    assert group(result, "arrays-hashing").attempted == 1


def test_since_keeps_the_weakness_of_today():
    attempts = [attempt("a", days_ago=10, attempt_id=1)]
    result = stats([problem("a")], attempts, since=TODAY)
    assert (
        group(result, "arrays-hashing").weakness
        == stats([problem("a")], attempts).groups[0].weakness
    )


def test_since_counts_finished_attempts_from_that_date():
    attempts = [attempt("a", days_ago=10, attempt_id=1), attempt("a", days_ago=1, attempt_id=2)]
    assert stats([problem("a")], attempts, since=TODAY - timedelta(days=1)).finished == 1


def test_finished_counts_attempts_outside_the_content_too():
    assert stats([problem("a")], [attempt("removed-problem")]).finished == 1


def test_last_seven_days_includes_today_and_six_days_before():
    attempts = [attempt("a", days_ago=days, attempt_id=days) for days in (0, 6, 7)]
    assert stats([problem("a")], attempts).last_7_days == 2


def test_due_today_and_overdue_count_in_scope_reviews():
    entries = [problem("a", progress=due(0)), problem("b", progress=due(-2)), problem("c")]
    result = stats(entries)
    assert (result.due_today, result.overdue) == (1, 1)


def test_bench_counts_the_latest_verdict_per_problem_and_language():
    bench = [
        BenchGrade("a", Language.PYTHON, Verdict.OPTIMAL, TODAY),
        BenchGrade("a", Language.JAVA, Verdict.SUBOPTIMAL, TODAY),
    ]
    assert stats([problem("a")], bench=bench).bench == {
        Verdict.OPTIMAL: 1,
        Verdict.NEAR_OPTIMAL: 0,
        Verdict.SUBOPTIMAL: 1,
        Verdict.UNKNOWN: 0,
    }


def test_bench_with_since_ignores_earlier_runs():
    bench = [BenchGrade("a", Language.PYTHON, Verdict.OPTIMAL, TODAY - timedelta(days=3))]
    result = stats([problem("a")], bench=bench, since=TODAY)
    assert result.bench[Verdict.OPTIMAL] == 0


@pytest.mark.parametrize(
    ("days_ago", "expected"),
    [((), 0), ((0,), 1), ((0, 1, 2), 3), ((1, 2), 2), ((0, 2), 1), ((2, 3), 0)],
)
def test_streak_ends_today_or_yesterday(days_ago, expected):
    days = {TODAY - timedelta(days=days) for days in days_ago}
    assert streak_days(days, TODAY) == expected
