"""`cstudy next`: pick what to practice (docs/specs/cli.md#cstudy-next).

The rules are pure (`coding_study.domain.next_selection`); this gathers their inputs from the
content and progress.db. Candidates are the problems in `problems/` and the non-autograded items
in `tracks/` of the tracks in scope.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.practice_catalog import practice_candidates
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.jdk_fit import cannot_run_text
from coding_study.domain.next_selection import (
    Candidate,
    JdkScope,
    NextPick,
    NextQuery,
    NextScope,
    NextSource,
    pick_next,
)
from coding_study.domain.precedence import resolve_language
from coding_study.domain.problem import Difficulty, Language, ProblemKind, ProblemMeta, Track
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


@dataclass(frozen=True, slots=True)
class NothingToPick:
    """`recommend` found nothing in scope."""

    jdk_reason: str | None = None
    """Why, when the selected JDK took out the problems that would have been picked; None when
    the scope itself holds nothing to pick."""


@dataclass(frozen=True, slots=True)
class Recommendation:
    """The pick with what `cstudy next --json` names beside it."""

    pick: NextPick
    title: str
    kind: EntryKind
    language: Language | None
    """The language `cstudy next --start` starts it in; None for an item."""


def next_source(new: bool, review: bool) -> NextSource:
    """The source of `--new` and `--review`; raises UsageError for both."""
    if new and review:
        raise UsageError("--new and --review exclude each other")
    if new:
        return NextSource.NEW_ONLY
    return NextSource.REVIEWS_ONLY if review else NextSource.ANY


@dataclass(frozen=True, slots=True)
class _Selection:
    """What `pick_next` takes: the candidates, the graded attempts and the query."""

    candidates: tuple[Candidate, ...]
    attempts: tuple[GradedAttempt, ...]
    query: NextQuery

    def pick(self) -> NextPick | None:
        return pick_next(self.candidates, self.attempts, self.query)


def next_problem(environment: Environment, request: NextRequest) -> NextPick | None:
    """Raises UsageError for a pattern outside the taxonomy."""
    return _selection(environment, request).pick()


def _selection(environment: Environment, request: NextRequest) -> _Selection:
    if request.pattern is not None and request.pattern not in PATTERNS:
        raise UsageError(f'unknown pattern "{request.pattern}"; see docs/specs/content.md')
    clock = environment.clock
    scope = NextScope(
        tracks=frozenset(request.tracks or environment.config.next.tracks),
        pattern=request.pattern,
        difficulty=request.difficulty,
        language=request.language,
        jdk=jdk_scope(environment, request.language),
    )
    query = NextQuery(scope, clock.local_date(clock.now()), request.source)
    candidates = practice_candidates(environment, scope.tracks)
    return _Selection(candidates, graded_attempts(environment), query)


def jdk_scope(environment: Environment, requested: Language | None) -> JdkScope:
    """The selected JDK and the language that `cstudy start` would start a problem in."""
    return JdkScope(environment.jdk.selected(), resolve_language(requested, environment.config))


def jdk_reason(
    environment: Environment,
    scope: NextScope,
    candidates: Sequence[Candidate],
    picks_without_jdk: Callable[[NextScope], bool],
) -> str | None:
    """Why the selected JDK left nothing to pick: None when the scope would hold nothing without
    it (`picks_without_jdk` says whether it would pick anything), or when it took out nothing."""
    languages = scope.blocked_languages(candidates)
    jdk = scope.jdk
    if jdk is None or not languages or not picks_without_jdk(replace(scope, jdk=None)):
        return None
    return cannot_run_text(jdk.selected, environment.jdk.unusable_java_home(), languages)


def recommend(environment: Environment, request: NextRequest) -> Recommendation | NothingToPick:
    """`next_problem`, with the pick's title, kind and start language, or why there is none."""
    selection = _selection(environment, request)
    picked = selection.pick()
    if picked is None:
        return NothingToPick(_nothing_because_of_the_jdk(environment, selection))
    candidate = picked.candidate
    if not candidate.autograded:
        item = environment.items.load(candidate.slug)
        return Recommendation(picked, item.title, EntryKind.ITEM, None)
    meta = environment.problems.load(candidate.slug).meta
    language = _problem_language(environment, meta, request.language)
    return Recommendation(picked, meta.title, entry_kind(meta.kind), language)


def _nothing_because_of_the_jdk(environment: Environment, selection: _Selection) -> str | None:
    query = selection.query

    def picks(scope: NextScope) -> bool:
        return (
            pick_next(selection.candidates, selection.attempts, replace(query, scope=scope))
            is not None
        )

    return jdk_reason(environment, query.scope, selection.candidates, picks)


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
    return _problem_language(environment, meta, requested)


def _problem_language(
    environment: Environment, meta: ProblemMeta, requested: Language | None
) -> Language:
    if meta.kind is ProblemKind.PROJECT:
        return project_language(meta)
    return resolve_language(requested, environment.config)
