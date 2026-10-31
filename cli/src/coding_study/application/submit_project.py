"""`cstudy submit`: grade a project problem and open its next level
(docs/specs/cli.md#cstudy-submit, progress-and-scheduling.md#project-attempts).

Every case of levels 1 to the unlocked level, visible and hidden, runs through the grading job and
is judged by the problem's comparator. Every submission is stored. One that graded every unlocked
level and passed every case opens the next level: it records the unlock, writes the level's test
file and rewrites the statement; at the last level it is the full pass. The time box is soft: a
submission is never refused.
"""

from dataclasses import dataclass, replace
from datetime import datetime

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.comparison import problem_comparator
from coding_study.application.environment import Environment
from coding_study.application.ports import ProgressNotice
from coding_study.application.project_runs import GradingRun, project_levels, run_grading
from coding_study.application.project_tests import LevelTestFile, LevelTestWriter
from coding_study.application.statement_file import write_statement
from coding_study.domain.attempts import Attempt, AttemptMode
from coding_study.domain.cases import Case
from coding_study.domain.comparators import Comparator
from coding_study.domain.diagnostics import Diagnostic, load_diagnostic
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Judgement
from coding_study.domain.levels import LevelRun, cases_up_to
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.project import level_methods, method_text
from coding_study.domain.project_manifest import project_lock
from coding_study.domain.signature import ClassSignature
from coding_study.domain.submissions import (
    LevelTally,
    LevelUnlock,
    SubmissionRecord,
    level_tallies,
)
from coding_study.domain.workspace_projects import project_folder

MILLISECONDS_PER_SECOND = 1000


@dataclass(frozen=True, slots=True)
class SubmitRequest:
    slug: str | None = None
    language: Language | None = None
    level: int | None = None
    """`--level N`: grade levels 1 to N; None grades every unlocked level."""


@dataclass(frozen=True, slots=True)
class OpenedLevel:
    """The level a submission opened."""

    level: int
    title: str
    methods: tuple[str, ...]
    """The methods the level adds, as the problem's language declares them."""
    tests: LevelTestFile
    statement: str
    """The statement's path, rewritten to show the level."""


@dataclass(frozen=True, slots=True)
class SubmitResult:
    meta: ProblemMeta
    attempt: Attempt
    """As stored after this submission."""
    language: Language
    cases: tuple[Case, ...]
    """The graded cases, in tests.json order."""
    judgement: Judgement
    comparator: Comparator
    levels: LevelRun
    """`ran_up_to` is the graded level; `newly_unlocked` says whether this submission opened one."""
    submission: SubmissionRecord
    opened: OpenedLevel | None
    duration_seconds: float

    @property
    def level_tallies(self) -> tuple[LevelTally, ...]:
        return self.submission.levels

    @property
    def every_level(self) -> bool:
        return self.submission.every_level

    @property
    def submitted_at(self) -> datetime:
        return self.submission.submitted_at

    @property
    def is_mock(self) -> bool:
        """A mock attempt names no hidden case, not even a failing one."""
        return self.attempt.mode is AttemptMode.MOCK

    @property
    def finished_every_level(self) -> bool:
        """The full pass: every case of every level passed."""
        progress = self.levels.progress
        return self.every_level and self.judgement.passed and progress.all_unlocked

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Where the project's code did not load (docs/specs/cli.md#diagnostics)."""
        error = self.judgement.load_error
        return (load_diagnostic(error),) if error else ()


def submit_project(
    environment: Environment, request: SubmitRequest, notify: ProgressNotice
) -> SubmitResult:
    """Raises UsageError without an attempt in progress, for another kind of problem or a locked
    level, and RunnerStartError (exit 4) when the toolchain cannot grade the project."""
    clock = environment.clock
    started = clock.monotonic()
    attempt = find_attempt(environment.progress, request.slug, request.language)
    language = autograded_language(attempt)
    problem = environment.problems.load(attempt.slug)
    meta = problem.meta
    require_project(meta)
    levels = project_levels(meta, attempt.level_unlocked, request.level)
    folder = project_folder(meta.slug)
    run = GradingRun(problem, language, environment.workspace.absolute(folder), levels.ran_up_to)
    judgement = run_grading(environment, run, notify)
    graded = cases_up_to(problem.cases, levels.ran_up_to)
    duration = clock.monotonic() - started
    submission = SubmissionRecord(
        attempt_id=attempt.id,
        submitted_at=clock.now(),
        code_hash=environment.workspace.content_hash(folder),
        graded_up_to=levels.ran_up_to,
        every_level=levels.ran_up_to == levels.unlocked,
        levels=level_tallies(graded, judgement),
        tally=judgement.tally(),
        duration_ms=round(duration * MILLISECONDS_PER_SECOND),
    )
    environment.progress.add_submission(submission)
    result = SubmitResult(
        meta=meta,
        attempt=attempt,
        language=language,
        cases=graded,
        judgement=judgement,
        comparator=problem_comparator(environment, meta),
        levels=levels,
        submission=submission,
        opened=None,
        duration_seconds=duration,
    )
    if not (submission.every_level and judgement.passed):
        return result
    with environment.workspace.locked(project_lock(meta.slug)):
        return _Opener(environment, problem, language).after_passing(result)


def require_project(meta: ProblemMeta) -> None:
    """Raises UsageError for a problem of another kind, which `cstudy test` grades."""
    if meta.kind is not ProblemKind.PROJECT:
        raise UsageError(f"cstudy submit is for project problems; cstudy test grades {meta.slug}")


class _Opener:
    """What a pass of every unlocked level changes: the next level, or the full pass."""

    def __init__(self, environment: Environment, problem: Problem, language: Language) -> None:
        self._environment = environment
        self._problem = problem
        self._language = language

    def after_passing(self, result: SubmitResult) -> SubmitResult:
        """Under the project's lock, against the attempt as stored now: a submission graded
        while another opened the level, or while `cstudy start --fresh` ended the attempt,
        opens nothing."""
        stored = self._environment.progress.in_progress_attempt(result.meta.slug, self._language)
        if stored is None or stored.id != result.attempt.id:
            return result
        result = replace(result, attempt=stored)
        if stored.level_unlocked != result.levels.unlocked:
            return result
        levels = result.levels.after_passing()
        if levels.newly_unlocked:
            return self._open(replace(result, levels=levels))
        if result.attempt.first_pass_at is not None:
            return result
        attempt = replace(result.attempt, first_pass_at=result.submitted_at)
        self._environment.progress.update_attempt(attempt)
        return replace(result, attempt=attempt)

    def _open(self, result: SubmitResult) -> SubmitResult:
        environment = self._environment
        level = result.levels.unlocked
        attempt = replace(result.attempt, level_unlocked=level)
        environment.progress.update_attempt(attempt)
        environment.progress.add_level_unlock(LevelUnlock(attempt.id, level, result.submitted_at))
        generator = environment.toolchains.project_test_generator(self._language)
        writer = LevelTestWriter(environment.workspace, generator)
        tests = writer.write_level(self._problem, project_folder(self._problem.meta.slug), level)
        statement = write_statement(environment, self._problem, level)
        opened = OpenedLevel(
            level=level,
            title=result.levels.progress.title(level),
            methods=self._methods(level),
            tests=tests,
            statement=statement,
        )
        return replace(result, attempt=attempt, opened=opened)

    def _methods(self, level: int) -> tuple[str, ...]:
        signature = self._problem.meta.signature
        if not isinstance(signature, ClassSignature):
            return ()
        methods = level_methods(signature, level)
        return tuple(method_text(method, self._language) for method in methods)
