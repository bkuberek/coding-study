"""What `cstudy next` picks (docs/specs/progress-and-scheduling.md#cstudy-next-selection).

Deterministic: the pick depends only on the candidates, the finished attempts, the date and
the flags, never on the order the rows arrive in. Every ordering below ends in a total order.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from fractions import Fraction

from coding_study.domain.items import ItemMeta
from coding_study.domain.problem import (
    ALL_LANGUAGES,
    DEFAULT_CURRICULUM_ORDER,
    ContentStatus,
    Difficulty,
    Language,
    ProblemMeta,
    Track,
)
from coding_study.domain.scheduling import ProblemProgress
from coding_study.domain.weakness import GradedAttempt, Group, GroupHistory, group_of

_DIFFICULTY_ORDER = tuple(Difficulty)
_GATES = {Difficulty.MEDIUM: Difficulty.EASY, Difficulty.HARD: Difficulty.MEDIUM}
"""A difficulty opens once a problem one level easier is passed, or when the group has none."""
_UNTOUCHED = ProblemProgress()


@dataclass(frozen=True, slots=True)
class Candidate:
    """Something `cstudy next` may pick: a problem or a non-autograded item, with its progress."""

    id: str | None
    """None for non-autograded items, which have no id."""
    slug: str
    track: Track
    difficulty: Difficulty
    patterns: tuple[str, ...] = ()
    order: int = DEFAULT_CURRICULUM_ORDER
    content: ContentStatus = ContentStatus.READY
    languages: tuple[Language, ...] = ALL_LANGUAGES
    """The problem's `languages`; items have none and need none."""
    progress: ProblemProgress = _UNTOUCHED

    @property
    def autograded(self) -> bool:
        return self.id is not None

    @property
    def group(self) -> Group:
        return group_of(self.track, self.patterns)

    @property
    def sort_id(self) -> str:
        """The `id` tie-break: the problem id, or the slug of an item."""
        return self.id or self.slug

    def sort_key(self) -> tuple[int, int, str, str]:
        """Difficulty, curriculum order, id; the slug makes the order total."""
        return _DIFFICULTY_ORDER.index(self.difficulty), self.order, self.sort_id, self.slug


def candidate_of(meta: ProblemMeta, progress: ProblemProgress) -> Candidate:
    return Candidate(
        id=meta.id,
        slug=meta.slug,
        track=meta.track,
        difficulty=meta.difficulty,
        patterns=meta.patterns,
        order=meta.order,
        content=meta.status,
        languages=meta.languages,
        progress=progress,
    )


def item_candidate_of(meta: ItemMeta, progress: ProblemProgress) -> Candidate:
    return Candidate(
        id=None,
        slug=meta.slug,
        track=meta.track,
        difficulty=meta.difficulty,
        order=meta.order,
        content=meta.status,
        languages=(),
        progress=progress,
    )


@dataclass(frozen=True, slots=True)
class NextScope:
    tracks: frozenset[Track]
    pattern: str | None = None
    """Matches any listed pattern."""
    difficulty: Difficulty | None = None
    language: Language | None = None
    """Problems whose `languages` include it; items stay in scope."""

    def includes(self, candidate: Candidate) -> bool:
        checks = (
            candidate.track in self.tracks,
            candidate.content is ContentStatus.READY,
            self.pattern is None or self.pattern in candidate.patterns,
            self.difficulty in (None, candidate.difficulty),
            self._offers_language(candidate),
        )
        return all(checks)

    def _offers_language(self, candidate: Candidate) -> bool:
        if self.language is None or not candidate.autograded:
            return True
        return self.language in candidate.languages


class NextSource(StrEnum):
    ANY = "any"
    REVIEWS_ONLY = "review"
    """`--review`: skip new problems."""
    NEW_ONLY = "new"
    """`--new`: skip reviews."""


@dataclass(frozen=True, slots=True)
class NextQuery:
    scope: NextScope
    today: date
    source: NextSource = NextSource.ANY


@dataclass(frozen=True, slots=True)
class ReviewPick:
    """Step 1: a due review."""

    candidate: Candidate
    overdue_days: int
    interval_days: int


@dataclass(frozen=True, slots=True)
class NewPick:
    """Step 2: a new problem from the weakest group."""

    candidate: Candidate
    group: Group
    weakness: Fraction


type NextPick = ReviewPick | NewPick


def pick_next(
    candidates: Sequence[Candidate], attempts: Sequence[GradedAttempt], query: NextQuery
) -> NextPick | None:
    """None is step 3: nothing due and no new problems in scope."""
    selection = _Selection(candidates, attempts, query)
    review = None if query.source is NextSource.NEW_ONLY else selection.review()
    if review is not None or query.source is NextSource.REVIEWS_ONLY:
        return review
    return selection.new_problem()


class _Selection:
    def __init__(
        self,
        candidates: Sequence[Candidate],
        attempts: Sequence[GradedAttempt],
        query: NextQuery,
    ) -> None:
        self._today = query.today
        self._in_scope = [candidate for candidate in candidates if query.scope.includes(candidate)]
        self._idle = [
            candidate for candidate in self._in_scope if not candidate.progress.in_progress
        ]
        self._groups: defaultdict[Group, list[Candidate]] = defaultdict(list)
        for candidate in self._in_scope:
            self._groups[candidate.group].append(candidate)
        group_by_slug = {candidate.slug: candidate.group for candidate in self._in_scope}
        self._attempts: defaultdict[Group, list[GradedAttempt]] = defaultdict(list)
        for attempt in attempts:
            if attempt.slug in group_by_slug:
                self._attempts[group_by_slug[attempt.slug]].append(attempt)

    def review(self) -> ReviewPick | None:
        due = [candidate for candidate in self._idle if candidate.progress.is_due(self._today)]
        if not due:
            return None
        chosen = min(due, key=self._review_rank)
        entry = chosen.progress.schedule
        assert entry is not None
        overdue = (self._today - entry.due_on).days
        return ReviewPick(chosen, overdue, entry.state.interval_days)

    def new_problem(self) -> NewPick | None:
        fresh = [candidate for candidate in self._idle if candidate.progress.is_new]
        if not fresh:
            return None
        group = min({candidate.group for candidate in fresh}, key=self._group_rank)
        in_group = [candidate for candidate in fresh if candidate.group == group]
        eligible = [candidate for candidate in in_group if self._is_open(candidate)]
        chosen = min(eligible or _lowest_difficulty(in_group), key=Candidate.sort_key)
        return NewPick(chosen, group, self.weakness(group))

    def weakness(self, group: Group) -> Fraction:
        problems = self._groups[group]
        mastered = sum(1 for candidate in problems if candidate.progress.is_mastered)
        return GroupHistory(len(problems), mastered, self._attempts[group]).weakness(self._today)

    def _review_rank(self, candidate: Candidate) -> tuple[Fraction, int, str, str]:
        """Highest priority first, then the smaller interval, then the id."""
        entry = candidate.progress.schedule
        assert entry is not None
        interval = max(entry.state.interval_days, 1)
        overdue = Fraction((self._today - entry.due_on).days + 1, interval)
        priority = overdue + self.weakness(candidate.group)
        return -priority, entry.state.interval_days, candidate.sort_id, candidate.slug

    def _group_rank(self, group: Group) -> tuple[Fraction, tuple[int, int, str]]:
        return -self.weakness(group), group.tie_break_key()

    def _is_open(self, candidate: Candidate) -> bool:
        easier = _GATES.get(candidate.difficulty)
        if easier is None:
            return True
        problems = self._groups[candidate.group]
        same = [problem for problem in problems if problem.difficulty is easier]
        return not same or any(problem.progress.has_passed for problem in same)


def _lowest_difficulty(candidates: Sequence[Candidate]) -> list[Candidate]:
    lowest = min(_DIFFICULTY_ORDER.index(candidate.difficulty) for candidate in candidates)
    return [
        candidate
        for candidate in candidates
        if _DIFFICULTY_ORDER.index(candidate.difficulty) == lowest
    ]
