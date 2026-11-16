"""`cstudy mock`: a timed mock interview (docs/specs/cli.md#cstudy-mock).

The picks follow the `cstudy next` rules over new medium and hard problems
(`coding_study.domain.mock_interview`); each starts like `cstudy start --fresh --timer`, with mode
`mock`. While the shared timer runs and a problem is unfinished, `cstudy hint`, `cstudy solution`
and another `cstudy mock` are locked.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from coding_study.application.environment import Environment
from coding_study.application.language_requirement import require_workspace_language
from coding_study.application.next_problem import (
    graded_attempts,
    jdk_reason,
    jdk_scope,
    reject_unknown_labels,
    starting_of,
)
from coding_study.application.practice_catalog import is_item, practice_candidates
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import SECONDS_PER_MINUTE, Attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.items import ItemMeta
from coding_study.domain.labels import LabelFilter
from coding_study.domain.mock_interview import new_in_scope, pick_mock, running_mock
from coding_study.domain.next_selection import (
    NewPick,
    NextQuery,
    NextScope,
    Starting,
    profile_effect,
)
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta, Track
from coding_study.domain.profile import (
    NO_PROFILE_EFFECT,
    NO_WIDENING,
    Profile,
    ProfileEffect,
    Widening,
)

DEFAULT_MINUTES = 45
DEFAULT_COUNT = 2


@dataclass(frozen=True, slots=True)
class MockRequest:
    minutes: int = DEFAULT_MINUTES
    count: int = DEFAULT_COUNT
    tracks: tuple[Track, ...] = ()
    """Empty: the config's `next.tracks`."""
    language: Language | None = None
    """`--lang`: only problems available in it, started in it. None: a pick starts in the default
    language (`default_lang` while it is a workspace language) when it lists it, else in the first
    workspace language it lists."""
    labels: LabelFilter = field(default_factory=LabelFilter)
    """`--domain` and `--role`; unlike in `cstudy next`, they do not widen the tracks."""
    profile: Profile | None = None
    """The learner profile that narrows the picks; None applies none."""
    widening: Widening = NO_WIDENING
    """The dimensions the profile is dropped in: `--widen`, and each explicit `--lang`, `--role` or
    `--domain`."""


@dataclass(frozen=True, slots=True)
class MockAttempt:
    """One problem of a mock interview: its attempt, and the problem it practices."""

    attempt: Attempt
    meta: ProblemMeta | ItemMeta

    @property
    def is_project(self) -> bool:
        return isinstance(self.meta, ProblemMeta) and self.meta.kind is ProblemKind.PROJECT


@dataclass(frozen=True, slots=True)
class MockProblem:
    pick: NewPick
    started: MockAttempt
    user_file: str
    """The stub, the folder of a project problem, or the notes of a rubric problem."""
    statement: str
    language: Language | None = None
    """The language it started in; None for a rubric problem."""

    @property
    def is_project(self) -> bool:
        return self.started.is_project


@dataclass(frozen=True, slots=True)
class MockSession:
    request: MockRequest
    language: Language
    """`--lang`, else the default language."""
    problems: tuple[MockProblem, ...]
    jdk_reason: str | None = None
    """Why nothing started, when the selected JDK took out the problems that would have: the
    reason `cstudy next` gives."""
    profile: ProfileEffect = NO_PROFILE_EFFECT
    """What the learner profile did to the problems the picks came from."""
    profile_left_nothing: bool = False
    """Nothing started, and the profile is why: without it there are picks."""

    @property
    def ends_at(self) -> datetime | None:
        """When the shared timer ends; None when nothing started."""
        ends = (_ends_at(problem.started.attempt) for problem in self.problems)
        return max(ends, default=None)


@dataclass(frozen=True, slots=True)
class CurrentMock:
    """The mock interview that runs, as its lock sees it: its unfinished problems, in the order
    they started, and its shared timer."""

    attempts: tuple[MockAttempt, ...]
    ends_at: datetime
    remaining: timedelta


def start_mock(environment: Environment, request: MockRequest) -> MockSession:
    """Raises UsageError while another mock interview runs."""
    require_no_running_mock(environment, "cstudy mock")
    scope = _scope(environment, request)
    starting = starting_of(environment, request.language)
    clock = environment.clock
    query = NextQuery(scope, clock.local_date(clock.now()))
    candidates = practice_candidates(environment, scope.tracks)
    attempts = graded_attempts(environment)
    effect = profile_effect(scope, lambda counted: len(new_in_scope(candidates, counted)))
    picks = pick_mock(candidates, attempts, query, request.count)
    if not picks:
        reason = jdk_reason(
            environment,
            scope,
            candidates,
            lambda open_scope: bool(
                pick_mock(candidates, attempts, replace(query, scope=open_scope), 1)
            ),
        )
        without_profile = not effect.narrowed.is_empty and bool(
            pick_mock(candidates, attempts, replace(query, scope=scope.without_profile()), 1)
        )
        return MockSession(request, starting.default, (), reason, effect, without_profile)
    timer_s = request.minutes * SECONDS_PER_MINUTE
    problems = tuple(_start(environment, pick, starting, timer_s) for pick in picks)
    return MockSession(request, starting.default, problems, profile=effect)


def mock_scope(environment: Environment, request: MockRequest) -> ProfileEffect:
    """How many of the new medium and hard problems the picks come from the learner profile
    leaves, of those it leaves without it; none while the profile narrows nothing in this run.
    Starts nothing."""
    scope = _scope(environment, request)
    candidates = practice_candidates(environment, scope.tracks)
    return profile_effect(scope, lambda counted: len(new_in_scope(candidates, counted)))


def _scope(environment: Environment, request: MockRequest) -> NextScope:
    """Raises UsageError for a language outside the workspace's, or a domain or job role outside
    its list."""
    if request.language is not None:
        require_workspace_language(environment, request.language)
    reject_unknown_labels(request.labels)
    starting = starting_of(environment, request.language)
    return NextScope(
        tracks=frozenset(request.tracks or environment.config.next.tracks),
        language=request.language,
        jdk=jdk_scope(environment, starting),
        labels=request.labels,
        starting=starting,
        profile=request.profile,
        widening=request.widening,
    )


def current_mock(environment: Environment) -> CurrentMock | None:
    """The mock interview whose timer runs, wherever it started; None when none does."""
    now = environment.clock.now()
    mock = running_mock(environment.progress.attempts_in_progress(), now)
    if mock is None:
        return None
    attempts = tuple(
        MockAttempt(attempt, _meta(environment, attempt.slug)) for attempt in mock.attempts
    )
    return CurrentMock(attempts, mock.ends_at, mock.remaining(now))


def require_no_running_mock(environment: Environment, command: str) -> None:
    """Raises UsageError naming the unfinished problems and the time left."""
    now = environment.clock.now()
    mock = running_mock(environment.progress.attempts_in_progress(), now)
    if mock is None:
        return
    minutes, seconds = divmod(int(mock.remaining(now).total_seconds()), SECONDS_PER_MINUTE)
    raise UsageError(
        f"{command} is locked during the mock interview ({', '.join(mock.slugs)}; "
        f"{minutes:02d}:{seconds:02d} left); it unlocks when the timer ends or every problem "
        "is done"
    )


def _start(
    environment: Environment, pick: NewPick, starting: Starting, timer_s: int
) -> MockProblem:
    slug = pick.candidate.slug
    if not pick.candidate.autograded:
        item = start_item_attempt(environment, ItemStartRequest(slug, True, timer_s, mock=True))
        started = MockAttempt(item.attempt, item.meta)
        return MockProblem(pick, started, item.notes_path, item.statement_path)
    language = starting.language_of(pick.candidate) or starting.default
    request = StartRequest(slug, language, fresh=True, timer_s=timer_s, mock=True)
    problem = start_attempt(environment, request)
    started = MockAttempt(problem.attempt, problem.problem.meta)
    return MockProblem(pick, started, problem.stub_path, problem.statement_path, language)


def _meta(environment: Environment, slug: str) -> ProblemMeta | ItemMeta:
    if is_item(environment, slug):
        return environment.items.load(slug)
    return environment.problems.load(slug).meta


def _ends_at(attempt: Attempt) -> datetime:
    assert attempt.time_limit_s is not None
    return attempt.started_at + timedelta(seconds=attempt.time_limit_s)
