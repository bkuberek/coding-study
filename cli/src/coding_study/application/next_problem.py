"""`cstudy next`: pick what to practice (docs/specs/cli.md#cstudy-next).

The rules are pure (`coding_study.domain.next_selection`); this gathers their inputs from the
content and progress.db. Candidates are the problems in `problems/` and the non-autograded items
in `tracks/` of the tracks in scope.
"""

from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.practice_catalog import practice_candidates
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.next_selection import (
    Candidate,
    NextPick,
    NextQuery,
    NextScope,
    NextSource,
    pick_next,
)
from coding_study.domain.precedence import resolve_language
from coding_study.domain.problem import Difficulty, Language, ProblemKind, Track
from coding_study.domain.project import project_language
from coding_study.domain.taxonomy import PATTERNS
from coding_study.domain.weakness import GradedAttempt


@dataclass(frozen=True, slots=True)
class NextRequest:
    tracks: tuple[Track, ...] = ()
    """Empty: the config's `next.tracks`."""
    pattern: str | None = None
    difficulty: Difficulty | None = None
    language: Language | None = None
    source: NextSource = NextSource.ANY


def next_problem(environment: Environment, request: NextRequest) -> NextPick | None:
    """Raises UsageError for a pattern outside the taxonomy."""
    if request.pattern is not None and request.pattern not in PATTERNS:
        raise UsageError(f'unknown pattern "{request.pattern}"; see docs/specs/content.md')
    clock = environment.clock
    scope = NextScope(
        tracks=frozenset(request.tracks or environment.config.next.tracks),
        pattern=request.pattern,
        difficulty=request.difficulty,
        language=request.language,
    )
    query = NextQuery(scope, clock.local_date(clock.now()), request.source)
    candidates = practice_candidates(environment, scope.tracks)
    return pick_next(candidates, graded_attempts(environment), query)


def graded_attempts(environment: Environment) -> tuple[GradedAttempt, ...]:
    """Every finished attempt with its grade, for the weakness score."""
    return tuple(
        graded
        for attempt in environment.progress.finished_attempts()
        if (graded := _graded(environment, attempt)) is not None
    )


def _graded(environment: Environment, attempt: Attempt) -> GradedAttempt | None:
    if attempt.grade is None or attempt.ended_at is None:
        return None
    ended_on = environment.clock.local_date(attempt.ended_at)
    return GradedAttempt(attempt.id, attempt.slug, attempt.grade, attempt.ended_at, ended_on)


def start_language(
    environment: Environment, candidate: Candidate, requested: Language | None
) -> Language | None:
    """The language `cstudy next --start` starts `candidate` in: a project problem's own, `--lang`
    or the config's `default_lang` for another problem, and none for an item."""
    if not candidate.autograded:
        return None
    meta = environment.problems.load(candidate.slug).meta
    if meta.kind is ProblemKind.PROJECT:
        return project_language(meta)
    return resolve_language(requested, environment.config)
