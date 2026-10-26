"""`cstudy start`: create or reopen a stub, render the statement, begin an attempt.

Specs: docs/specs/cli.md#cstudy-start, runners.md#stub-generation and
progress-and-scheduling.md#attempt-lifecycle.
"""

from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.statement_file import write_statement
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus, NewAttempt
from coding_study.domain.buggy_stubs import buggy_as_stub, buggy_file
from coding_study.domain.errors import ContentError, ContentIssue, UsageError
from coding_study.domain.levels import FIRST_LEVEL, LevelProgress, level_progress
from coding_study.domain.precedence import resolve_language
from coding_study.domain.problem import Language, Problem, StubSource


@dataclass(frozen=True, slots=True)
class StartRequest:
    slug: str
    language: Language | None = None
    """None: the config's `default_lang`."""
    fresh: bool = False
    timer_s: int | None = None
    mock: bool = False
    """Started by `cstudy mock`: a new attempt gets mode `mock`."""


@dataclass(frozen=True, slots=True)
class StartedAttempt:
    problem: Problem
    attempt: Attempt
    stub_path: str
    statement_path: str
    resumed: bool
    created_stub: bool
    archived_to: str | None = None

    @property
    def levels(self) -> LevelProgress | None:
        """Progressive problems: the levels this attempt has unlocked."""
        return level_progress(self.problem.meta, self.attempt.level_unlocked)


def start_attempt(environment: Environment, request: StartRequest) -> StartedAttempt:
    problem = environment.problems.load(request.slug)
    language = resolve_language(request.language, environment.config)
    _require_language(problem, language)
    stub_path = layout.stub_path(problem.meta, language)
    in_progress = environment.progress.in_progress_attempt(request.slug, language)
    if in_progress is not None and not request.fresh:
        created = _ensure_stub(environment, problem, language)
        statement = write_statement(environment, problem, in_progress.level_unlocked)
        return StartedAttempt(problem, in_progress, stub_path, statement, True, created)
    started = _Start(environment, problem, language, request).begin(in_progress)
    write_statement(environment, problem, started.attempt.level_unlocked)
    return started


def attempt_mode(mock: bool, scheduled: bool) -> AttemptMode:
    """`mock` under `cstudy mock`, `review` once the problem has a schedule entry, else `new`
    (docs/specs/progress-and-scheduling.md#attempt-lifecycle)."""
    if mock:
        return AttemptMode.MOCK
    return AttemptMode.REVIEW if scheduled else AttemptMode.NEW


def _require_language(problem: Problem, language: Language) -> None:
    if language not in problem.meta.languages:
        available = ", ".join(problem.meta.languages)
        raise UsageError(f"{problem.meta.slug} is not available in {language}; use {available}")


def _ensure_stub(environment: Environment, problem: Problem, language: Language) -> bool:
    """Writes the stub when its file is missing; True when it did."""
    path = layout.stub_path(problem.meta, language)
    if environment.workspace.exists(path):
        return False
    environment.workspace.write_text(path, _stub_text(environment, problem, language))
    return True


def _stub_text(environment: Environment, problem: Problem, language: Language) -> str:
    meta = problem.meta
    if meta.stub is StubSource.GENERATED:
        return environment.toolchains.stub_generator(language).generate(meta)
    name = buggy_file(language)
    text = environment.files.read_text(meta.slug, name)
    if text is None:
        directory = environment.files.problem_directory(meta.slug)
        raise ContentError([ContentIssue(f"{directory}/{name}", "", "missing (stub: buggy)")])
    return buggy_as_stub(meta, language, text)


class _Start:
    """A new attempt, archiving the previous file for `--fresh` and review attempts."""

    def __init__(
        self,
        environment: Environment,
        problem: Problem,
        language: Language,
        request: StartRequest,
    ) -> None:
        self._environment = environment
        self._problem = problem
        self._language = language
        self._request = request
        self._stub_path = layout.stub_path(problem.meta, language)

    def begin(self, in_progress: Attempt | None) -> StartedAttempt:
        progress = self._environment.progress
        slug = self._problem.meta.slug
        mode = attempt_mode(self._request.mock, progress.schedule_entry(slug) is not None)
        replaces_file = self._request.fresh or mode is AttemptMode.REVIEW
        archive = replaces_file and self._environment.workspace.exists(self._stub_path)
        new_stub = archive or not self._environment.workspace.exists(self._stub_path)
        stub_text = _stub_text(self._environment, self._problem, self._language) if new_stub else ""
        previous = progress.latest_attempt(slug, self._language)
        if in_progress is not None:
            self._abandon(in_progress)
        attempt = progress.add_attempt(self._new_attempt(mode))
        archived_to = self._archive(previous or attempt) if archive else None
        opened = replace(attempt, archive_path=archived_to, level_unlocked=self._first_level())
        if opened != attempt:
            attempt = opened
            progress.update_attempt(attempt)
        if new_stub:
            self._environment.workspace.write_text(self._stub_path, stub_text)
        statement = layout.statement_path(slug)
        return StartedAttempt(
            self._problem, attempt, self._stub_path, statement, False, new_stub, archived_to
        )

    def _new_attempt(self, mode: AttemptMode) -> NewAttempt:
        return NewAttempt(
            slug=self._problem.meta.slug,
            language=self._language,
            mode=mode,
            started_at=self._environment.clock.now(),
            time_limit_s=self._request.timer_s,
            stub_path=self._stub_path,
        )

    def _first_level(self) -> int | None:
        """Progressive problems start with level 1 unlocked."""
        return FIRST_LEVEL if level_progress(self._problem.meta, None) else None

    def _abandon(self, attempt: Attempt) -> None:
        ended = replace(
            attempt, status=AttemptStatus.ABANDONED, ended_at=self._environment.clock.now()
        )
        self._environment.progress.update_attempt(ended)

    def _archive(self, owner: Attempt) -> str:
        """Moves the stub into the archive directory of the attempt that wrote it."""
        directory = layout.archive_directory(owner.slug, owner.id, self._language)
        return self._environment.workspace.move_into(self._stub_path, directory)
