"""`cstudy next` resumes first (docs/specs/progress-and-scheduling.md#cstudy-next-selection): the
attempt in progress used most recently, among those in scope, before a review or a new problem."""

from datetime import UTC, date, datetime, timedelta

from coding_study.domain.next_selection import (
    Candidate,
    NextScope,
    OpenAttempt,
    ResumePick,
    pick_resume,
)
from coding_study.domain.problem import Difficulty, Language, Track

DSA_ONLY = NextScope(frozenset({Track.DSA}))
MORNING = datetime(2026, 10, 24, 9, tzinfo=UTC)
TODAY = date(2026, 10, 24)


def candidate(slug: str, track: Track = Track.DSA) -> Candidate:
    return Candidate("0001", slug, track, Difficulty.EASY, patterns=("arrays-hashing",))


def open_attempt(
    slug: str, attempt_id: int, used_at: datetime = MORNING, track: Track = Track.DSA
) -> OpenAttempt:
    return OpenAttempt(candidate(slug, track), attempt_id, Language.PYTHON, used_at, TODAY)


def resume(*attempts: OpenAttempt, scope: NextScope = DSA_ONLY) -> ResumePick | None:
    return pick_resume(attempts, scope)


def test_nothing_in_progress_resumes_nothing():
    assert resume() is None


def test_the_only_attempt_in_progress_is_resumed():
    only = open_attempt("two-sum", 1)
    assert resume(only) == ResumePick(only)


def test_the_attempt_used_most_recently_wins():
    older = open_attempt("older", 1, MORNING)
    newer = open_attempt("newer", 2, MORNING - timedelta(hours=3))
    assert resume(newer, older) == ResumePick(older, (newer,))


def test_equal_use_goes_to_the_later_attempt():
    first = open_attempt("first", 1)
    second = open_attempt("second", 2)
    assert resume(first, second) == ResumePick(second, (first,))


def test_the_others_come_most_recently_used_first():
    used = [open_attempt(f"p{n}", n, MORNING + timedelta(hours=n)) for n in (1, 2, 3, 4)]
    found = resume(*used)
    assert found is not None
    assert [other.attempt_id for other in found.others] == [3, 2, 1]


def test_an_attempt_outside_the_scope_is_not_resumed():
    elsewhere = open_attempt("design", 1, track=Track.SYSTEM_DESIGN)
    assert resume(elsewhere) is None


def test_an_attempt_outside_the_scope_is_not_offered_as_another():
    inside = open_attempt("inside", 1)
    elsewhere = open_attempt("design", 2, MORNING + timedelta(hours=1), Track.SYSTEM_DESIGN)
    assert resume(inside, elsewhere) == ResumePick(inside)


def test_the_pick_is_the_candidate_of_the_attempt():
    only = open_attempt("two-sum", 1)
    found = resume(only)
    assert found is not None
    assert found.candidate.slug == "two-sum"
