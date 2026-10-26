"""`cstudy list`: problems with their progress, filtered (docs/specs/cli.md#cstudy-list)."""

from dataclasses import dataclass
from datetime import date

from coding_study.application.environment import Environment
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

    def matches(self, summary: ProblemSummary, status: ProblemStatus) -> bool:
        meta = summary.meta
        checks = (
            self.track in (None, meta.track),
            self.pattern is None or self.pattern in meta.patterns,
            self.difficulty in (None, meta.difficulty),
            self.status in (None, status),
            self.content in (None, meta.status),
            self.language is None or self.language in summary.reference_languages,
        )
        return all(checks)


@dataclass(frozen=True, slots=True)
class ListedProblem:
    summary: ProblemSummary
    status: ProblemStatus
    due_on: date | None


def list_problems(
    environment: Environment, problem_filter: ProblemFilter
) -> tuple[ListedProblem, ...]:
    progress = environment.progress.problem_progress()
    today = environment.clock.local_date(environment.clock.now())
    listed = (
        _listed(summary, progress.get(summary.meta.slug, ProblemProgress()), today)
        for summary in environment.problems.list_summaries()
    )
    return tuple(item for item in listed if problem_filter.matches(item.summary, item.status))


def _listed(summary: ProblemSummary, progress: ProblemProgress, today: date) -> ListedProblem:
    due_on = progress.schedule.due_on if progress.schedule else None
    return ListedProblem(summary, progress.status(today), due_on)
