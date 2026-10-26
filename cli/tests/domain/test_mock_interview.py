from datetime import UTC, date, datetime, timedelta

from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus
from coding_study.domain.mock_interview import pick_mock, running_mock
from coding_study.domain.next_selection import Candidate, NextQuery, NextScope
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemProgress

TODAY = date(2026, 10, 24)
NOW = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
QUERY = NextQuery(NextScope(frozenset({Track.DSA})), TODAY)
IN_PROGRESS = ProblemProgress(frozenset({AttemptStatus.IN_PROGRESS}))
FORTY_FIVE_MINUTES = 45 * 60


def problem(
    slug: str, pattern: str = "arrays-hashing", difficulty: Difficulty = Difficulty.MEDIUM, **fields
) -> Candidate:
    return Candidate("0001", slug, Track.DSA, difficulty, (pattern,), **fields)


def picked(*candidates: Candidate, count: int = 2) -> list[str]:
    return [pick.candidate.slug for pick in pick_mock(candidates, (), QUERY, count)]


def mock_attempt(slug: str, minutes_ago: int = 0, **fields: object) -> Attempt:
    started = NOW - timedelta(minutes=minutes_ago)
    defaults: dict[str, object] = {
        "status": AttemptStatus.IN_PROGRESS,
        "time_limit_s": FORTY_FIVE_MINUTES,
    }
    defaults.update(fields)
    return Attempt(1, slug, Language.PYTHON, AttemptMode.MOCK, started_at=started, **defaults)  # type: ignore[arg-type]


def test_mock_picks_count_problems():
    assert picked(problem("a"), problem("b", "stack"), problem("c", "trees")) == ["a", "b"]


def test_mock_skips_easy_problems():
    assert picked(problem("a", difficulty=Difficulty.EASY), problem("b"), count=1) == ["b"]


def test_mock_takes_hard_problems():
    assert picked(problem("a", difficulty=Difficulty.HARD), count=1) == ["a"]


def test_mock_prefers_a_new_group_for_each_problem():
    candidates = (problem("a"), problem("b"), problem("c", "stack"))
    assert picked(*candidates) == ["a", "c"]


def test_mock_reuses_a_group_when_no_other_has_new_problems():
    assert picked(problem("a"), problem("b")) == ["a", "b"]


def test_mock_picks_fewer_when_scope_runs_out():
    assert picked(problem("a"), count=3) == ["a"]


def test_mock_skips_problems_in_progress():
    assert picked(problem("a", progress=IN_PROGRESS), problem("b"), count=1) == ["b"]


def test_mock_picks_new_problems_only():
    passed = ProblemProgress(frozenset({AttemptStatus.PASSED}))
    assert picked(problem("a", progress=passed), problem("b"), count=1) == ["b"]


def test_no_mock_runs_without_mock_attempts():
    assert running_mock((), NOW) is None


def test_a_mock_runs_while_its_timer_has_time_left():
    mock = running_mock((mock_attempt("a", 10), mock_attempt("b", 10)), NOW)
    assert mock is not None
    assert (mock.slugs, mock.remaining(NOW)) == (("a", "b"), timedelta(minutes=35))


def test_a_mock_ends_with_its_timer():
    assert running_mock((mock_attempt("a", 45),), NOW) is None


def test_a_mock_ends_when_every_problem_is_done():
    assert running_mock((mock_attempt("a", 10, status=AttemptStatus.PASSED),), NOW) is None


def test_a_mock_runs_until_its_last_problem_is_done():
    attempts = (mock_attempt("a", 10, status=AttemptStatus.PASSED), mock_attempt("b", 10))
    mock = running_mock(attempts, NOW)
    assert mock is not None
    assert mock.slugs == ("b",)


def test_other_attempts_do_not_make_a_mock():
    attempt = Attempt(1, "a", Language.PYTHON, AttemptMode.NEW, AttemptStatus.IN_PROGRESS, NOW)
    assert running_mock((attempt,), NOW) is None
