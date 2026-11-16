"""`cstudy list`: problems with their progress, filtered (docs/specs/cli.md#cstudy-list)."""

from collections import defaultdict
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date

from coding_study.application.environment import Environment
from coding_study.domain.attempts import Attempt
from coding_study.domain.checked_by import CheckedBy, checked_by_of
from coding_study.domain.items import RUBRIC_KINDS, EntryKind, entry_kind
from coding_study.domain.jdk import SelectedJdk
from coding_study.domain.jdk_fit import fit_of, listing_reason
from coding_study.domain.labels import LabelFilter, Labels
from coding_study.domain.levels import level_progress
from coding_study.domain.problem import (
    ContentStatus,
    Difficulty,
    Language,
    ProblemMeta,
    ProblemSummary,
    Track,
)
from coding_study.domain.problem_sets import ProblemSet
from coding_study.domain.profile import NO_WIDENING, NarrowedValues, Profile, Widening
from coding_study.domain.scheduling import ProblemProgress, ProblemStatus
from coding_study.domain.service_project import NEEDS_NOTHING, need_markers


@dataclass(frozen=True, slots=True)
class ProblemFilter:
    """Every set field must match."""

    track: Track | None = None
    pattern: str | None = None
    """Matches any of the problem's patterns."""
    difficulty: Difficulty | None = None
    status: ProblemStatus | None = None
    content: ContentStatus | None = None
    language: Language | None = None
    """Problems with a reference in this language."""
    kind: EntryKind | None = None
    """A rubric kind keeps the rubric problems of that kind only; an autograded kind leaves them
    out."""
    labels: LabelFilter = field(default_factory=LabelFilter)
    """`--domain`, `--role` and `--scope`; an entry without labels matches none that is set."""
    in_set: ProblemSet | None = None
    """`--set`: only its entries, which the callers then put in its order."""
    search: str | None = None
    """`--search`: a text the slug or the title holds, in any case."""
    needs: str | None = None
    """`--needs`: `none`, or `docker` or a service a problem needs."""
    checked_by: CheckedBy | None = None
    """`--checked-by`: problems checked this way (docs/specs/compatibility.md#checked-by)."""
    profile: Profile | None = None
    """The learner profile that narrows the rows; None applies none, as under `--set`
    (docs/specs/cli.md#the-learner-profile)."""
    widening: Widening = NO_WIDENING
    """The dimensions the profile is dropped in: `--widen`, and each explicit `--lang`, `--role` or
    `--domain`."""

    @property
    def lists_rubric_problems(self) -> bool:
        """Whether the kind leaves room for rubric problems, which `list_items` filters further. A
        rubric problem needs nothing and is checked by its rubric."""
        return (
            (self.kind is None or self.kind in RUBRIC_KINDS)
            and self.needs in (None, NEEDS_NOTHING)
            and self.checked_by in (None, CheckedBy.RUBRIC)
        )

    def matches(self, summary: ProblemSummary, status: ProblemStatus) -> bool:
        meta = summary.meta
        checks = (
            self.track in (None, meta.track),
            self.pattern is None or self.pattern in meta.patterns,
            self.difficulty in (None, meta.difficulty),
            self.status in (None, status),
            self.content in (None, meta.status),
            self.language is None or self.language in summary.reference_languages,
            self.kind in (None, entry_kind(meta.kind)),
            self.labels.matches(meta.labels),
            self.holds(meta.slug),
            self.finds(meta.slug, meta.title),
            self._needed(meta),
            self._checked(summary),
            self.in_profile(meta.labels, summary.reference_languages),
        )
        return all(checks)

    def in_profile(self, labels: Labels, languages: Collection[Language]) -> bool:
        """Whether the learner profile keeps an entry with these labels and reference languages."""
        return self.profile is None or self.profile.matches(
            labels, languages, widening=self.widening
        )

    def narrowed(self) -> NarrowedValues:
        """The profile values that narrow this run; none without a profile."""
        if self.profile is None:
            return NarrowedValues()
        return self.profile.narrowed(widening=self.widening)

    def without_profile(self) -> "ProblemFilter":
        """The same filter as `--widen all` would leave it."""
        return replace(self, profile=None)

    def _needed(self, meta: ProblemMeta) -> bool:
        markers = need_markers(meta)
        if self.needs is None:
            return True
        return not markers if self.needs == NEEDS_NOTHING else self.needs in markers

    def _checked(self, summary: ProblemSummary) -> bool:
        if self.checked_by is None:
            return True
        kind = entry_kind(summary.meta.kind)
        return self.checked_by in checked_by_of(kind, summary.has_rubric)

    def holds(self, slug: str) -> bool:
        return self.in_set is None or self.in_set.holds(slug)

    def finds(self, slug: str, title: str) -> bool:
        if self.search is None:
            return True
        wanted = self.search.strip().lower()
        return wanted in slug.lower() or wanted in title.lower()


@dataclass(frozen=True, slots=True)
class ProfileEffect:
    """What the learner profile did to a listing: `shown` rows of the `total` that `--widen all`
    would show with the same other filters."""

    narrowed: NarrowedValues
    shown: int
    total: int

    @property
    def hidden(self) -> int:
        return self.total - self.shown


@dataclass(frozen=True, slots=True)
class ListedProblem:
    summary: ProblemSummary
    status: ProblemStatus
    due_on: date | None
    blocked: tuple[Language, ...] = ()
    """The reference languages that the selected JDK cannot run for this problem: Java and Kotlin,
    when the JDK is outside the problem's range."""
    levels: "ListedLevels | None" = None
    """A progressive or project problem's levels; None for another."""


@dataclass(frozen=True, slots=True)
class ListedLevels:
    """How far a problem with levels has come (progress-and-scheduling.md#mastery-per-level)."""

    last: int
    passed: int
    """The most levels a pass reached, in any language."""
    mastered: int
    """The levels it is mastered through."""


@dataclass(frozen=True, slots=True)
class JdkNote:
    """The footer of `cstudy list`: the languages it marked, and why."""

    languages: tuple[Language, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class ListingContext:
    """What `cstudy list --json` adds to the rows."""

    today: date
    """The local date the statuses are of."""
    in_progress: Mapping[str, tuple[Attempt, ...]]
    """Each slug's attempts in progress, earliest start first; slugs without one are absent."""


def list_problems(
    environment: Environment, problem_filter: ProblemFilter
) -> tuple[ListedProblem, ...]:
    """The matching problems in the order of `cstudy list` (docs/specs/compatibility.md#order)."""
    progress = environment.progress.problem_progress()
    today = environment.clock.local_date(environment.clock.now())
    selected = environment.jdk.selected()
    listed = (
        _listed(summary, progress.get(summary.meta.slug, ProblemProgress()), today, selected)
        for summary in sorted(
            environment.problems.list_summaries(), key=lambda summary: summary.meta.listing_key()
        )
    )
    return tuple(item for item in listed if problem_filter.matches(item.summary, item.status))


def jdk_note(environment: Environment, problems: Sequence[ListedProblem]) -> JdkNote | None:
    """None when no language is marked."""
    blocked = {language for problem in problems for language in problem.blocked}
    if not blocked:
        return None
    jdk = environment.jdk
    reason = listing_reason(jdk.selected(), jdk.unusable_java_home())
    return JdkNote(tuple(language for language in Language if language in blocked), reason)


def listing_context(environment: Environment) -> ListingContext:
    in_progress: defaultdict[str, list[Attempt]] = defaultdict(list)
    for attempt in environment.progress.attempts_in_progress():
        in_progress[attempt.slug].append(attempt)
    today = environment.clock.local_date(environment.clock.now())
    return ListingContext(today, {slug: tuple(found) for slug, found in in_progress.items()})


def _listed(
    summary: ProblemSummary, progress: ProblemProgress, today: date, selected: SelectedJdk | None
) -> ListedProblem:
    due_on = progress.schedule.due_on if progress.schedule else None
    blocked = fit_of(selected, None, summary.meta.jdk).blocked(summary.reference_languages)
    return ListedProblem(
        summary, progress.status(today), due_on, blocked, listed_levels(summary.meta, progress)
    )


def listed_levels(meta: ProblemMeta, progress: ProblemProgress) -> ListedLevels | None:
    levels = level_progress(meta, None)
    if levels is None:
        return None
    last = levels.last
    return ListedLevels(last, progress.levels_passed(last), progress.mastered_levels(last))
