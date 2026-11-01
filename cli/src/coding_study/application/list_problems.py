"""`cstudy list`: problems with their progress, filtered (docs/specs/cli.md#cstudy-list)."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from coding_study.application.environment import Environment
from coding_study.domain.attempts import Attempt
from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.jdk import SelectedJdk
from coding_study.domain.jdk_fit import fit_of, listing_reason
from coding_study.domain.problem import (
    ContentStatus,
    Difficulty,
    Language,
    ProblemSummary,
    Track,
)
from coding_study.domain.scheduling import ProblemProgress, ProblemStatus


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
    """`item` keeps the non-autograded items only; a kind of problem leaves them out."""

    @property
    def lists_items(self) -> bool:
        """Whether the kind leaves room for items, which `list_items` filters further."""
        return self.kind in (None, EntryKind.ITEM)

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
        )
        return all(checks)


@dataclass(frozen=True, slots=True)
class ListedProblem:
    summary: ProblemSummary
    status: ProblemStatus
    due_on: date | None
    blocked: tuple[Language, ...] = ()
    """The reference languages that the selected JDK cannot run for this problem: Java and Kotlin,
    when the JDK is outside the problem's range."""


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
    progress = environment.progress.problem_progress()
    today = environment.clock.local_date(environment.clock.now())
    selected = environment.jdk.selected()
    listed = (
        _listed(summary, progress.get(summary.meta.slug, ProblemProgress()), today, selected)
        for summary in environment.problems.list_summaries()
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
    return ListedProblem(summary, progress.status(today), due_on, blocked)
