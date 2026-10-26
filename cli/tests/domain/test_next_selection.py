from datetime import UTC, date, datetime, timedelta
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from coding_study.domain.attempts import AttemptStatus, Grade
from coding_study.domain.items import ItemMeta
from coding_study.domain.next_selection import (
    Candidate,
    NewPick,
    NextQuery,
    NextScope,
    NextSource,
    ReviewPick,
    item_candidate_of,
    pick_next,
)
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemProgress, ReviewState, ScheduleEntry
from coding_study.domain.weakness import GradedAttempt, Group

TODAY = date(2026, 10, 24)
DSA_ONLY = NextScope(frozenset({Track.DSA}))
SYSTEM_DESIGN_ONLY = NextScope(frozenset({Track.SYSTEM_DESIGN}))
NEW = ProblemProgress()
IN_PROGRESS = ProblemProgress(frozenset({AttemptStatus.IN_PROGRESS}))
PATTERNS = ("arrays-hashing", "two-pointers", "sliding-window", "stack")


def candidate(slug: str, problem_id: str = "0001", **fields: object) -> Candidate:
    defaults: dict[str, object] = {"difficulty": Difficulty.EASY, "patterns": ("arrays-hashing",)}
    defaults.update(fields)
    return Candidate(problem_id, slug, Track(defaults.pop("track", Track.DSA)), **defaults)  # type: ignore[arg-type]


def item(slug: str, **fields: object) -> Candidate:
    """A ready system design item: no id, no patterns, no languages."""
    defaults: dict[str, object] = {"difficulty": Difficulty.MEDIUM, "languages": ()}
    defaults.update(fields)
    return Candidate(None, slug, Track.SYSTEM_DESIGN, **defaults)  # type: ignore[arg-type]


def scheduled(
    due_in_days: int, interval: int = 3, grade: Grade = Grade.OK, *statuses: AttemptStatus
) -> ProblemProgress:
    state = ReviewState(interval_days=interval, reps=1)
    entry = ScheduleEntry(
        "any", state, TODAY + timedelta(days=due_in_days), grade, datetime(2026, 10, 1, tzinfo=UTC)
    )
    return ProblemProgress(frozenset(statuses or {AttemptStatus.PASSED}), entry)


def graded(slug: str, grade: Grade, attempt_id: int = 1) -> GradedAttempt:
    return GradedAttempt(attempt_id, slug, grade, datetime(2026, 10, 24, 9, tzinfo=UTC), TODAY)


def pick(
    *candidates: Candidate,
    attempts: tuple[GradedAttempt, ...] = (),
    scope: NextScope = DSA_ONLY,
    source: NextSource = NextSource.ANY,
):
    return pick_next(candidates, attempts, NextQuery(scope, TODAY, source))


def picked_slug(*candidates: Candidate, **options: object) -> str | None:
    result = pick(*candidates, **options)  # type: ignore[arg-type]
    return result.candidate.slug if result is not None else None


def test_nothing_in_scope_picks_nothing():
    assert pick() is None


def test_a_due_review_comes_before_new_problems():
    due = candidate("due", "0002", progress=scheduled(0))
    assert picked_slug(candidate("fresh"), due) == "due"


def test_new_skips_reviews():
    due = candidate("due", "0002", progress=scheduled(0))
    assert picked_slug(candidate("fresh"), due, source=NextSource.NEW_ONLY) == "fresh"


def test_review_skips_new_problems():
    assert picked_slug(candidate("fresh"), source=NextSource.REVIEWS_ONLY) is None


def test_a_review_not_due_yet_is_not_picked():
    later = candidate("later", progress=scheduled(1))
    assert picked_slug(later, source=NextSource.REVIEWS_ONLY) is None


def test_reviews_overdue_longer_relative_to_their_interval_win():
    week = candidate("week", "0001", progress=scheduled(-3, interval=7))
    day = candidate("day", "0002", progress=scheduled(0, interval=1))
    assert picked_slug(week, day) == "day"


def test_reviews_in_weaker_groups_win():
    strong = candidate("strong", "0001", progress=scheduled(0))
    weak = candidate("weak", "0002", patterns=("stack",), progress=scheduled(0))
    attempts = (graded("strong", Grade.OK, 1), graded("weak", Grade.AGAIN, 2))
    assert picked_slug(strong, weak, attempts=attempts) == "weak"


def test_review_ties_go_to_the_smaller_interval():
    longer = candidate("longer", "0001", progress=scheduled(-1, interval=2))
    shorter = candidate("shorter", "0002", progress=scheduled(0, interval=1))
    assert picked_slug(longer, shorter) == "shorter"


def test_review_ties_then_go_to_the_lower_id():
    second = candidate("second", "0002", progress=scheduled(0))
    first = candidate("first", "0001", progress=scheduled(0))
    assert picked_slug(second, first) == "first"


def test_a_review_reports_its_overdue_days():
    result = pick(candidate("due", progress=scheduled(-3, interval=7)))
    assert isinstance(result, ReviewPick)
    assert result.overdue_days == 3


def test_problems_in_progress_are_never_picked():
    busy = candidate("busy", "0001", progress=scheduled(0, 3, Grade.OK, AttemptStatus.IN_PROGRESS))
    assert picked_slug(busy, candidate("idle", "0002", progress=IN_PROGRESS)) is None


def test_untouched_groups_come_before_a_group_just_passed():
    done = candidate("done", "0001", progress=scheduled(3))
    sibling = candidate("sibling", "0002")
    other = candidate("other", "0003", patterns=("stack",))
    attempts = (graded("done", Grade.OK),)
    assert picked_slug(done, sibling, other, attempts=attempts) == "other"


def test_a_group_just_failed_comes_before_untouched_groups():
    progress = scheduled(1, 1, Grade.AGAIN, AttemptStatus.FAILED)
    failed = candidate("failed", "0001", patterns=("stack",), progress=progress)
    sibling = candidate("sibling", "0002", patterns=("stack",))
    other = candidate("other", "0003")
    attempts = (graded("failed", Grade.AGAIN),)
    assert picked_slug(failed, sibling, other, attempts=attempts) == "sibling"


def test_equally_weak_groups_follow_the_taxonomy_order():
    later = candidate("later", "0001", patterns=("two-pointers",))
    earlier = candidate("earlier", "0002", patterns=("arrays-hashing",))
    assert picked_slug(later, earlier) == "earlier"


def test_a_new_pick_reports_its_group_and_weakness():
    result = pick(candidate("fresh", patterns=("stack", "arrays-hashing")))
    assert isinstance(result, NewPick)
    assert (result.group, result.weakness) == (Group(Track.DSA, "stack"), Fraction(3, 4))


def test_easy_problems_come_first():
    medium = candidate("medium", "0001", difficulty=Difficulty.MEDIUM)
    easy = candidate("easy", "0002", difficulty=Difficulty.EASY)
    assert picked_slug(medium, easy) == "easy"


def test_medium_opens_once_an_easy_is_passed():
    easy = candidate("easy", "0001", progress=scheduled(5))
    medium = candidate("medium", "0002", difficulty=Difficulty.MEDIUM)
    hard = candidate("hard", "0003", difficulty=Difficulty.HARD)
    assert picked_slug(easy, medium, hard) == "medium"


def test_medium_is_open_in_a_group_without_easy_problems():
    medium = candidate("medium", "0002", difficulty=Difficulty.MEDIUM, order=5)
    hard = candidate("hard", "0001", difficulty=Difficulty.HARD, order=1)
    assert picked_slug(hard, medium) == "medium"


def test_hard_opens_in_a_group_without_medium_problems():
    easy = candidate("easy", "0001", progress=scheduled(5))
    hard = candidate("hard", "0002", difficulty=Difficulty.HARD)
    assert picked_slug(easy, hard) == "hard"


def test_hard_opens_once_a_medium_is_passed_even_while_medium_is_closed():
    easy = candidate("easy", "0001", progress=scheduled(1, 1, Grade.AGAIN, AttemptStatus.FAILED))
    passed = candidate("passed", "0002", difficulty=Difficulty.MEDIUM, progress=scheduled(5))
    medium = candidate("medium", "0003", difficulty=Difficulty.MEDIUM)
    hard = candidate("hard", "0004", difficulty=Difficulty.HARD)
    assert picked_slug(easy, passed, medium, hard) == "hard"


def test_a_gate_that_excludes_everything_falls_back_to_the_lowest_difficulty():
    easy = candidate("easy", "0001", progress=IN_PROGRESS)
    hard = candidate("hard", "0002", difficulty=Difficulty.HARD)
    medium = candidate("medium", "0003", difficulty=Difficulty.MEDIUM)
    assert picked_slug(easy, hard, medium) == "medium"


def test_curriculum_order_comes_before_the_id():
    later = candidate("later", "0001", order=2)
    sooner = candidate("sooner", "0002", order=1)
    assert picked_slug(later, sooner) == "sooner"


def test_drafts_are_out_of_scope():
    assert picked_slug(candidate("draft", content=ContentStatus.DRAFT)) is None


def test_other_tracks_are_out_of_scope():
    assert picked_slug(candidate("design", track=Track.LLD, patterns=())) is None


def test_listed_tracks_are_in_scope():
    scope = NextScope(frozenset({Track.LLD}))
    assert picked_slug(candidate("design", track=Track.LLD, patterns=()), scope=scope) == "design"


def test_the_pattern_filter_matches_any_listed_pattern():
    scope = NextScope(frozenset({Track.DSA}), pattern="monotonic-stack")
    window = candidate("window", patterns=("sliding-window", "monotonic-stack"))
    assert picked_slug(window, scope=scope) == "window"


def test_the_pattern_filter_excludes_other_patterns():
    scope = NextScope(frozenset({Track.DSA}), pattern="monotonic-stack")
    assert picked_slug(candidate("plain"), scope=scope) is None


def test_the_difficulty_filter():
    scope = NextScope(frozenset({Track.DSA}), difficulty=Difficulty.MEDIUM)
    assert picked_slug(candidate("easy"), scope=scope) is None


def test_the_language_filter_uses_the_problem_languages():
    scope = NextScope(frozenset({Track.DSA}), language=Language.KOTLIN)
    subset = candidate("subset", languages=(Language.PYTHON, Language.JAVA))
    assert picked_slug(subset, scope=scope) is None


def test_an_item_candidate_has_no_id_and_no_languages():
    meta = ItemMeta(
        "url-shortener",
        "URL Shortener",
        Track.SYSTEM_DESIGN,
        Difficulty.MEDIUM,
        45,
        ContentStatus.READY,
        order=1,
    )
    built = item_candidate_of(meta, IN_PROGRESS)
    assert built == item("url-shortener", order=1, progress=IN_PROGRESS)


def test_an_item_is_not_autograded():
    assert (item("url-shortener").autograded, candidate("two-sum").autograded) == (False, True)


def test_an_item_ties_on_its_slug_for_an_id():
    assert item("url-shortener").sort_id == "url-shortener"


def test_a_new_item_is_picked_from_its_track_group():
    result = pick(item("url-shortener"), scope=SYSTEM_DESIGN_ONLY)
    assert isinstance(result, NewPick)
    assert (result.candidate.slug, result.group) == ("url-shortener", Group(Track.SYSTEM_DESIGN))


def test_a_due_item_is_reviewed():
    due = item("url-shortener", progress=scheduled(-2, interval=3))
    result = pick(item("chat"), due, scope=SYSTEM_DESIGN_ONLY)
    assert result == ReviewPick(due, 2, 3)


def test_item_review_ties_go_to_the_lower_slug():
    second = item("rate-limiter", progress=scheduled(0))
    first = item("news-feed", progress=scheduled(0))
    assert picked_slug(second, first, scope=SYSTEM_DESIGN_ONLY) == "news-feed"


def test_new_items_in_the_same_order_tie_on_the_slug():
    later, earlier = item("rate-limiter", order=1), item("news-feed", order=1)
    assert picked_slug(later, earlier, scope=SYSTEM_DESIGN_ONLY) == "news-feed"


def test_equally_weak_pattern_groups_come_before_track_groups():
    scope = NextScope(frozenset({Track.DSA, Track.SYSTEM_DESIGN}))
    assert picked_slug(item("url-shortener"), candidate("two-sum"), scope=scope) == "two-sum"


def test_the_language_filter_keeps_items_in_scope():
    scope = NextScope(frozenset({Track.SYSTEM_DESIGN}), language=Language.KOTLIN)
    assert picked_slug(item("url-shortener"), scope=scope) == "url-shortener"


def test_the_pattern_filter_excludes_items():
    scope = NextScope(frozenset({Track.SYSTEM_DESIGN}), pattern="arrays-hashing")
    assert picked_slug(item("url-shortener"), scope=scope) is None


def test_attempts_outside_the_scope_do_not_change_weakness():
    result = pick(candidate("fresh"), attempts=(graded("elsewhere", Grade.AGAIN),))
    assert isinstance(result, NewPick)
    assert result.weakness == Fraction(3, 4)


# Determinism: the same database snapshot, date and flags give the same pick, whatever order
# the rows arrive in (docs/specs/progress-and-scheduling.md#cstudy-next-selection).

_TRACKS = (Track.DSA, Track.PRACTICAL, Track.SYSTEM_DESIGN)
_statuses = st.frozensets(st.sampled_from(AttemptStatus))
_schedules = st.one_of(
    st.none(),
    st.builds(
        lambda due, interval, grade: ScheduleEntry(
            "any",
            ReviewState(interval_days=interval, reps=1),
            TODAY + timedelta(days=due),
            grade,
            datetime(2026, 10, 1, tzinfo=UTC),
        ),
        st.integers(-10, 10),
        st.integers(1, 40),
        st.sampled_from(Grade),
    ),
)


@st.composite
def _candidates(draw: st.DrawFn) -> tuple[Candidate, ...]:
    count = draw(st.integers(0, 12))
    return tuple(
        Candidate(
            id=draw(st.sampled_from((None, "0001", "0002", "0003", f"{index:04d}"))),
            slug=f"p{index}",
            track=draw(st.sampled_from(_TRACKS)),
            difficulty=draw(st.sampled_from(Difficulty)),
            patterns=tuple(draw(st.lists(st.sampled_from(PATTERNS), max_size=2, unique=True))),
            order=draw(st.sampled_from((1, 2, 1000))),
            content=draw(st.sampled_from(ContentStatus)),
            languages=tuple(draw(st.lists(st.sampled_from(Language), min_size=1, unique=True))),
            progress=ProblemProgress(draw(_statuses), draw(_schedules)),
        )
        for index in range(count)
    )


@st.composite
def _attempts(draw: st.DrawFn, slugs: int) -> tuple[GradedAttempt, ...]:
    count = draw(st.integers(0, 15))
    attempts: list[GradedAttempt] = []
    for attempt_id in range(count):
        days_ago = draw(st.integers(0, 60))
        ended_on = TODAY - timedelta(days=days_ago)
        ended_at = datetime(ended_on.year, ended_on.month, ended_on.day, tzinfo=UTC)
        slug = f"p{draw(st.integers(0, max(slugs, 1)))}"
        grade = draw(st.sampled_from(Grade))
        attempts.append(GradedAttempt(attempt_id, slug, grade, ended_at, ended_on))
    return tuple(attempts)


_queries = st.builds(
    NextQuery,
    st.builds(
        NextScope,
        st.frozensets(st.sampled_from(_TRACKS), min_size=1),
        st.one_of(st.none(), st.sampled_from(PATTERNS)),
        st.one_of(st.none(), st.sampled_from(Difficulty)),
        st.one_of(st.none(), st.sampled_from(Language)),
    ),
    st.just(TODAY),
    st.sampled_from(NextSource),
)


@st.composite
def _snapshots(draw: st.DrawFn):
    candidates = draw(_candidates())
    attempts = draw(_attempts(len(candidates)))
    shuffled_candidates = tuple(draw(st.permutations(candidates)))
    shuffled_attempts = tuple(draw(st.permutations(attempts)))
    return candidates, attempts, shuffled_candidates, shuffled_attempts, draw(_queries)


@given(_snapshots())
def test_the_pick_does_not_depend_on_row_order(snapshot):
    candidates, attempts, shuffled_candidates, shuffled_attempts, query = snapshot
    first = pick_next(candidates, attempts, query)
    assert pick_next(shuffled_candidates, shuffled_attempts, query) == first


@given(_snapshots())
def test_the_pick_is_always_in_scope_and_idle(snapshot):
    candidates, attempts, _, _, query = snapshot
    result = pick_next(candidates, attempts, query)
    if result is not None:
        assert query.scope.includes(result.candidate)
        assert not result.candidate.progress.in_progress


@pytest.mark.parametrize("source", list(NextSource))
def test_repeated_picks_agree(source):
    candidates = (candidate("a", "0001"), candidate("b", "0002", progress=scheduled(0)))
    query = NextQuery(DSA_ONLY, TODAY, source)
    assert pick_next(candidates, (), query) == pick_next(candidates, (), query)
