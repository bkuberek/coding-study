"""What `cstudy next` picks (docs/specs/progress-and-scheduling.md#cstudy-next-selection).

Deterministic: the pick depends only on the candidates, the finished attempts, the date and
the flags, never on the order the rows arrive in. Every ordering below ends in a total order.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum
from fractions import Fraction

from coding_study.domain.items import ItemMeta
from coding_study.domain.jdk import DeclaredJdk, SelectedJdk
from coding_study.domain.jdk_fit import fit_of
from coding_study.domain.labels import LabelFilter, Labels
from coding_study.domain.layout import JVM_LANGUAGES
from coding_study.domain.levels import level_progress
from coding_study.domain.problem import (
    ALL_LANGUAGES,
    DEFAULT_CURRICULUM_ORDER,
    ContentStatus,
    Difficulty,
    Language,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.problem_sets import ProblemSet, target_reached
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
    jdk: DeclaredJdk | None = None
    """The JDK range the problem declares for its Java and Kotlin."""
    project: bool = False
    """A project problem, which starts in its own language, not in `--lang`."""
    labels: Labels = field(default_factory=Labels)
    levels: int | None = None
    """A progressive or project problem's last level; None for anything else."""

    @property
    def autograded(self) -> bool:
        return self.id is not None

    @property
    def group(self) -> Group:
        return group_of(self.track, self.patterns)

    def start_language(self, chosen: Language) -> Language | None:
        """The language `cstudy next --start` starts it in; None for an item."""
        if not self.autograded:
            return None
        return self.languages[0] if self.project and self.languages else chosen

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
        jdk=meta.jdk,
        project=meta.kind is ProblemKind.PROJECT,
        labels=meta.labels,
        levels=_last_level(meta),
    )


def _last_level(meta: ProblemMeta) -> int | None:
    levels = level_progress(meta, None)
    return levels.last if levels else None


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
        labels=meta.labels,
    )


@dataclass(frozen=True, slots=True)
class JdkScope:
    """The selected JDK, and the language `cstudy start` starts a problem in (`--lang`, else
    `default_lang`): a problem whose Java or Kotlin that JDK cannot run is out of scope, so the
    pick is never one that `cstudy start` would refuse."""

    selected: SelectedJdk | None
    language: Language

    def admits(self, candidate: Candidate) -> bool:
        language = candidate.start_language(self.language)
        if language not in JVM_LANGUAGES:
            return True
        return fit_of(self.selected, None, candidate.jdk).runs

    def blocked_language(self, candidate: Candidate) -> Language | None:
        """The Java or Kotlin that `candidate` would start in, when the JDK cannot run it."""
        language = candidate.start_language(self.language)
        return language if language is not None and not self.admits(candidate) else None


@dataclass(frozen=True, slots=True)
class NextScope:
    tracks: frozenset[Track]
    pattern: str | None = None
    """Matches any listed pattern."""
    difficulty: Difficulty | None = None
    language: Language | None = None
    """Problems whose `languages` include it; items stay in scope."""
    jdk: JdkScope | None = None
    """None: the selected JDK does not narrow the scope."""
    labels: LabelFilter = field(default_factory=LabelFilter)
    """`--domain`, `--role` and `--scope`; items and problems both carry labels."""

    def includes(self, candidate: Candidate) -> bool:
        checks = (
            candidate.track in self.tracks,
            candidate.content is ContentStatus.READY,
            self.pattern is None or self.pattern in candidate.patterns,
            self.difficulty in (None, candidate.difficulty),
            self._offers_language(candidate),
            self.labels.matches(candidate.labels),
            self.jdk is None or self.jdk.admits(candidate),
        )
        return all(checks)

    def blocked_languages(self, candidates: Iterable[Candidate]) -> tuple[Language, ...]:
        """The Java and Kotlin that `candidates` would start in, had the scope not left them out
        for the selected JDK alone."""
        if self.jdk is None:
            return ()
        open_scope = replace(self, jdk=None)
        blocked = {
            language
            for candidate in candidates
            if open_scope.includes(candidate)
            and (language := self.jdk.blocked_language(candidate)) is not None
        }
        return tuple(language for language in Language if language in blocked)

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


@dataclass(frozen=True, slots=True)
class SetPick:
    """`cstudy next --set`: the first entry in the set's order that isn't passed."""

    candidate: Candidate
    set_name: str
    position: int
    """From 1, among the set's entries that are candidates."""
    total: int


type NextPick = ReviewPick | NewPick


@dataclass(frozen=True, slots=True)
class OpenAttempt:
    """An attempt in progress, with the problem it works on."""

    candidate: Candidate
    attempt_id: int
    language: Language | None
    """None for an item."""
    used_at: datetime
    """The later of its start and its last test run."""
    used_on: date
    """`used_at` as the local date that the reason names."""


@dataclass(frozen=True, slots=True)
class ResumePick:
    """Step 0, before reviews and new problems: the attempt in progress used most recently."""

    attempt: OpenAttempt
    others: tuple[OpenAttempt, ...] = ()
    """The other attempts in progress in scope, the most recently used first."""

    @property
    def candidate(self) -> Candidate:
        return self.attempt.candidate


def pick_resume(attempts: Iterable[OpenAttempt], scope: NextScope) -> ResumePick | None:
    """The attempt in progress used most recently among those in `scope`; a tie goes to the later
    attempt. None when none is in progress there."""
    in_scope = [attempt for attempt in attempts if scope.includes(attempt.candidate)]
    ranked = sorted(
        in_scope, key=lambda attempt: (attempt.used_at, attempt.attempt_id), reverse=True
    )
    return ResumePick(ranked[0], tuple(ranked[1:])) if ranked else None


def pick_next(
    candidates: Sequence[Candidate], attempts: Sequence[GradedAttempt], query: NextQuery
) -> NextPick | None:
    """None is step 3: nothing due and no new problems in scope."""
    selection = _Selection(candidates, attempts, query)
    review = None if query.source is NextSource.NEW_ONLY else selection.review()
    if review is not None or query.source is NextSource.REVIEWS_ONLY:
        return review
    return selection.new_problem()


def pick_in_set(
    candidates: Sequence[Candidate],
    attempts: Sequence[GradedAttempt],
    query: NextQuery,
    problem_set: ProblemSet,
) -> SetPick | ReviewPick | None:
    """The first entry in the set's order that isn't passed, then a due review of the set, ranked
    as ever: `query` and `candidates` are those of a query without the set, so no weakness score
    changes (docs/specs/progress-and-scheduling.md#with---set)."""
    selection = _Selection(candidates, attempts, query)
    if query.source is not NextSource.REVIEWS_ONLY:
        pick = selection.first_not_passed(candidates, problem_set)
        if pick is not None or query.source is NextSource.NEW_ONLY:
            return pick
    return selection.review(problem_set.slugs)


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

    def first_not_passed(
        self, candidates: Sequence[Candidate], problem_set: ProblemSet
    ) -> SetPick | None:
        idle = {candidate.slug: candidate for candidate in self._idle}
        known = {candidate.slug for candidate in candidates}
        entries = [slug for slug in problem_set.slugs if slug in known]
        for position, slug in enumerate(entries, start=1):
            candidate = idle.get(slug)
            if candidate is not None and not self._done(candidate, problem_set):
                return SetPick(candidate, problem_set.name, position, len(entries))
        return None

    @staticmethod
    def _done(candidate: Candidate, problem_set: ProblemSet) -> bool:
        """A pass reached the entry's target level, every level by default."""
        target = problem_set.target_of(candidate.slug)
        return target_reached(candidate.progress, candidate.levels, target)

    def review(self, within: Collection[str] | None = None) -> ReviewPick | None:
        """The due review with the highest priority, of the slugs `within` when given."""
        due = [
            candidate
            for candidate in self._idle
            if candidate.progress.is_due(self._today)
            and (within is None or candidate.slug in within)
        ]
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
