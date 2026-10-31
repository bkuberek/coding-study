"""`cstudy mock`: a timed mock interview (docs/specs/cli.md#cstudy-mock).

The picks follow the `cstudy next` rules over new medium and hard problems
(`coding_study.domain.mock_interview`); each starts like `cstudy start --fresh --timer`, with mode
`mock`. While the shared timer runs and a problem is unfinished, `cstudy hint`, `cstudy solution`
and another `cstudy mock` are locked.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from coding_study.application.environment import Environment
from coding_study.application.next_problem import graded_attempts
from coding_study.application.practice_catalog import is_item, practice_candidates
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import SECONDS_PER_MINUTE, Attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.items import ItemMeta
from coding_study.domain.mock_interview import pick_mock, running_mock
from coding_study.domain.next_selection import NewPick, NextQuery, NextScope
from coding_study.domain.precedence import resolve_language
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta, Track

DEFAULT_MINUTES = 45
DEFAULT_COUNT = 2


@dataclass(frozen=True, slots=True)
class MockRequest:
    minutes: int = DEFAULT_MINUTES
    count: int = DEFAULT_COUNT
    tracks: tuple[Track, ...] = ()
    """Empty: the config's `next.tracks`."""
    language: Language | None = None
    """None: the config's `default_lang`."""


@dataclass(frozen=True, slots=True)
class MockAttempt:
    """One problem of a mock interview: its attempt, and the problem or item it practises."""

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
    """The stub, the folder of a project problem, or the notes of a non-autograded item."""
    statement: str

    @property
    def is_project(self) -> bool:
        return self.started.is_project


@dataclass(frozen=True, slots=True)
class MockSession:
    request: MockRequest
    language: Language
    problems: tuple[MockProblem, ...]

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
    clock = environment.clock
    language = resolve_language(request.language, environment.config)
    scope = NextScope(
        tracks=frozenset(request.tracks or environment.config.next.tracks), language=language
    )
    query = NextQuery(scope, clock.local_date(clock.now()))
    candidates = practice_candidates(environment, scope.tracks)
    picks = pick_mock(candidates, graded_attempts(environment), query, request.count)
    timer_s = request.minutes * SECONDS_PER_MINUTE
    problems = tuple(_start(environment, pick, language, timer_s) for pick in picks)
    return MockSession(request, language, problems)


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
    environment: Environment, pick: NewPick, language: Language, timer_s: int
) -> MockProblem:
    slug = pick.candidate.slug
    if not pick.candidate.autograded:
        item = start_item_attempt(environment, ItemStartRequest(slug, True, timer_s, mock=True))
        started = MockAttempt(item.attempt, item.meta)
        return MockProblem(pick, started, item.notes_path, item.statement_path)
    request = StartRequest(slug, language, fresh=True, timer_s=timer_s, mock=True)
    problem = start_attempt(environment, request)
    started = MockAttempt(problem.attempt, problem.problem.meta)
    return MockProblem(pick, started, problem.stub_path, problem.statement_path)


def _meta(environment: Environment, slug: str) -> ProblemMeta | ItemMeta:
    if is_item(environment, slug):
        return environment.items.load(slug)
    return environment.problems.load(slug).meta


def _ends_at(attempt: Attempt) -> datetime:
    assert attempt.time_limit_s is not None
    return attempt.started_at + timedelta(seconds=attempt.time_limit_s)
