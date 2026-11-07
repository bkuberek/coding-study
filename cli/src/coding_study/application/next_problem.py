"""`cstudy next`: pick what to practice (docs/specs/cli.md#cstudy-next).

The rules are pure (`coding_study.domain.next_selection`); this gathers their inputs from the
content and progress.db. Candidates are the problems in `problems/` and the non-autograded items
in `tracks/` of the tracks in scope.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from coding_study.application.environment import Environment
from coding_study.application.practice_catalog import practice_candidates
from coding_study.application.problem_sets import find_set, set_standing
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.jdk_fit import cannot_run_text
from coding_study.domain.labels import LabelFilter
from coding_study.domain.next_selection import (
    Candidate,
    JdkScope,
    NextPick,
    NextQuery,
    NextScope,
    NextSource,
    OpenAttempt,
    ResumePick,
    SetPick,
    pick_in_set,
    pick_next,
    pick_resume,
)
from coding_study.domain.precedence import resolve_language
from coding_study.domain.problem import (
    ContentStatus,
    Difficulty,
    Language,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.problem_sets import ProblemSet, SetStanding
from coding_study.domain.project import project_language
from coding_study.domain.taxonomy import DOMAINS, JOB_ROLES, PATTERNS
from coding_study.domain.weakness import GradedAttempt


@dataclass(frozen=True, slots=True)
class NextRequest:
    tracks: tuple[Track, ...] = ()
    """Empty: the config's `next.tracks`, or every track when `labels` is set."""
    pattern: str | None = None
    difficulty: Difficulty | None = None
    language: Language | None = None
    source: NextSource = NextSource.ANY
    labels: LabelFilter = field(default_factory=LabelFilter)
    set_name: str | None = None
    """`--set`: pick from this set, in its order."""


@dataclass(frozen=True, slots=True)
class NothingToPick:
    """`recommend` found nothing in scope."""

    jdk_reason: str | None = None
    """Why, when the selected JDK took out the problems that would have been picked; None when
    the scope itself holds nothing to pick."""
    set_standing: SetStanding | None = None
    """How the set stands, under `--set`."""


@dataclass(frozen=True, slots=True)
class Recommendation:
    """The pick with what `cstudy next --json` names beside it."""

    pick: NextPick | SetPick | ResumePick
    title: str
    kind: EntryKind
    language: Language | None
    """The language `cstudy next --start` starts it in, which is the language of the attempt a
    resume picks up; None for an item."""
    set_standing: SetStanding | None = None
    """How the set stands, under `--set`."""


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
    in_set: ProblemSet | None = None

    def pick(self) -> NextPick | SetPick | None:
        return self.pick_in(self.query.scope)

    def pick_in(self, scope: NextScope) -> NextPick | SetPick | None:
        query = replace(self.query, scope=scope)
        if self.in_set is None:
            return pick_next(self.candidates, self.attempts, query)
        return pick_in_set(self.candidates, self.attempts, query, self.in_set)

    def holds(self, slug: str) -> bool:
        return self.in_set is None or self.in_set.holds(slug)


def next_problem(environment: Environment, request: NextRequest) -> NextPick | SetPick | None:
    """Raises UsageError for a pattern, domain or job role outside its list."""
    return _selection(environment, request).pick()


def _selection(environment: Environment, request: NextRequest) -> _Selection:
    _reject_unknown_values(request)
    clock = environment.clock
    scope = NextScope(
        tracks=frozenset(_tracks_in_scope(environment, request)),
        pattern=request.pattern,
        difficulty=request.difficulty,
        language=request.language,
        jdk=jdk_scope(environment, request.language),
        labels=request.labels,
    )
    query = NextQuery(scope, clock.local_date(clock.now()), request.source)
    candidates = practice_candidates(environment, scope.tracks)
    in_set = None if request.set_name is None else find_set(environment, request.set_name)
    return _Selection(
        _with_chosen_ready(candidates, in_set), graded_attempts(environment), query, in_set
    )


def _with_chosen_ready(
    candidates: tuple[Candidate, ...], in_set: ProblemSet | None
) -> tuple[Candidate, ...]:
    """A draft of your own that you put in a set stays in it: `cstudy start` takes a draft, and a
    hand-picked list means what it says."""
    if in_set is None:
        return candidates
    return tuple(
        replace(candidate, content=ContentStatus.READY)
        if in_set.holds(candidate.slug)
        else candidate
        for candidate in candidates
    )


def _reject_unknown_values(request: NextRequest) -> None:
    if request.pattern is not None and request.pattern not in PATTERNS:
        raise UsageError(f'unknown pattern "{request.pattern}"; see docs/specs/content.md')
    domain, role = request.labels.domain, request.labels.role
    if domain is not None and domain not in DOMAINS:
        raise UsageError(f'unknown domain "{domain}"; use one of {", ".join(DOMAINS)}')
    if role is not None and role not in JOB_ROLES:
        raise UsageError(f'unknown job role "{role}"; use one of {", ".join(JOB_ROLES)}')


def _tracks_in_scope(environment: Environment, request: NextRequest) -> Sequence[Track]:
    """`--track` as given; else every track for a label filter or a set, since the configured
    tracks (`dsa`, by default) would leave out what a domain, role, scope or set names; else the
    config's."""
    if request.tracks:
        return request.tracks
    if request.labels.is_set or request.set_name is not None:
        return tuple(Track)
    return environment.config.next.tracks


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
    """What to practice: the attempt in progress used most recently, else `next_problem`'s pick
    (`--new` and `--review` force theirs), with its title, kind and start language; or why there
    is none."""
    selection = _selection(environment, request)
    in_set = selection.in_set
    standing = None if in_set is None else set_standing(environment, in_set)
    resumed = _resume(environment, selection) if request.source is NextSource.ANY else None
    picked = resumed or selection.pick()
    if picked is None:
        return NothingToPick(_nothing_because_of_the_jdk(environment, selection), standing)
    candidate = picked.candidate
    if not candidate.autograded:
        item = environment.items.load(candidate.slug)
        return Recommendation(picked, item.title, EntryKind.ITEM, None, standing)
    meta = environment.problems.load(candidate.slug).meta
    language = _problem_language(environment, meta, request.language)
    if resumed is not None:
        language = resumed.attempt.language or language
    return Recommendation(picked, meta.title, entry_kind(meta.kind), language, standing)


def _resume(environment: Environment, selection: _Selection) -> ResumePick | None:
    """The attempt in progress used most recently, among those whose problem is in scope."""
    by_slug = {candidate.slug: candidate for candidate in selection.candidates}
    open_attempts = [
        _open_attempt(environment, attempt, by_slug[attempt.slug])
        for attempt in environment.progress.attempts_in_progress()
        if attempt.slug in by_slug and selection.holds(attempt.slug)
    ]
    return pick_resume(open_attempts, selection.query.scope)


def _open_attempt(environment: Environment, attempt: Attempt, candidate: Candidate) -> OpenAttempt:
    """Used when it started, or when its last test ran if that came later."""
    last_run = environment.progress.latest_test_run(attempt.id)
    used_at = max(attempt.started_at, last_run.ran_at) if last_run else attempt.started_at
    used_on = environment.clock.local_date(used_at)
    return OpenAttempt(candidate, attempt.id, attempt.language, used_at, used_on)


def _nothing_because_of_the_jdk(environment: Environment, selection: _Selection) -> str | None:
    def picks(scope: NextScope) -> bool:
        return selection.pick_in(scope) is not None

    candidates = [
        candidate for candidate in selection.candidates if selection.holds(candidate.slug)
    ]
    return jdk_reason(environment, selection.query.scope, candidates, picks)


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
