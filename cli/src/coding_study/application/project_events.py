"""The events of `cstudy test --events` and `cstudy submit --events` on a project problem
(docs/specs/cli.md#event-stream).

A stream names its run once the run's options are checked, passes each progress notice on as it
happens, then reports what the run found: every test, or every graded case the attempt may show,
in run order; the diagnostics; each graded level; and the level a submission opened. The command
that writes the stream ends it with the outcome and the exit code, which are the command's own.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.environment import Environment
from coding_study.application.ports import ProgressNotice
from coding_study.application.project_runs import project_levels
from coding_study.application.project_testing import (
    ProjectTestRequest,
    ProjectTestResult,
    run_project_tests,
)
from coding_study.application.submit_project import (
    OpenedLevel,
    SubmitRequest,
    SubmitResult,
    require_project,
    submit_project,
)
from coding_study.domain.attempts import Attempt
from coding_study.domain.diagnostics import Diagnostic
from coding_study.domain.judging import CaseVerdict
from coding_study.domain.levels import LevelRun
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.project_test_runs import SuiteTestVerdict
from coding_study.domain.submissions import LevelTally


class RunCommand(StrEnum):
    TEST = "test"
    SUBMIT = "submit"


@dataclass(frozen=True, slots=True)
class RunStarted:
    """The run's options are checked and its work begins."""

    command: RunCommand
    meta: ProblemMeta
    attempt: Attempt
    language: Language
    levels: LevelRun
    """`ran_up_to` is the last level the run covers."""


@dataclass(frozen=True, slots=True)
class OutputLine:
    """A progress notice, such as `computing expected values ...`."""

    text: str


@dataclass(frozen=True, slots=True)
class SuiteTestReported:
    """One test of the native suite (`cstudy test`)."""

    verdict: SuiteTestVerdict


@dataclass(frozen=True, slots=True)
class CaseGraded:
    """One graded case (`cstudy submit`)."""

    verdict: CaseVerdict
    level: int | None


@dataclass(frozen=True, slots=True)
class DiagnosticFound:
    diagnostic: Diagnostic


@dataclass(frozen=True, slots=True)
class LevelGraded:
    tally: LevelTally


@dataclass(frozen=True, slots=True)
class LevelOpened:
    opened: OpenedLevel


type ProjectEvent = (
    RunStarted
    | OutputLine
    | SuiteTestReported
    | CaseGraded
    | DiagnosticFound
    | LevelGraded
    | LevelOpened
)
type EventSink = Callable[[ProjectEvent], None]


def stream_project_tests(
    environment: Environment, request: ProjectTestRequest, emit: EventSink
) -> ProjectTestResult:
    """Raises as `run_project_tests`: a locked level before any event; a `--case` that names no
    test, or a toolchain that cannot run the suite, after the start."""
    subject = _Subject.find(environment, request)
    emit(subject.started(RunCommand.TEST, request.level))
    result = run_project_tests(environment, request, _notices(emit))
    for verdict in result.verdicts:
        emit(SuiteTestReported(verdict))
    for diagnostic in result.diagnostics:
        emit(DiagnosticFound(diagnostic))
    return result


def stream_submission(
    environment: Environment, request: SubmitRequest, emit: EventSink
) -> SubmitResult:
    """Raises as `submit_project`: another kind of problem or a locked level before any event; a
    toolchain that cannot grade the project after the start."""
    subject = _Subject.find(environment, request)
    require_project(subject.meta)
    emit(subject.started(RunCommand.SUBMIT, request.level))
    result = submit_project(environment, request, _notices(emit))
    levels = {case.id: case.level for case in result.cases}
    for verdict in _shown(result):
        emit(CaseGraded(verdict, levels.get(verdict.case.id)))
    for diagnostic in result.diagnostics:
        emit(DiagnosticFound(diagnostic))
    for tally in result.level_tallies:
        emit(LevelGraded(tally))
    if result.opened is not None:
        emit(LevelOpened(result.opened))
    return result


@dataclass(frozen=True, slots=True)
class _Subject:
    """The attempt a run works on, and its problem."""

    attempt: Attempt
    meta: ProblemMeta

    @classmethod
    def find(cls, environment: Environment, request: ProjectTestRequest | SubmitRequest) -> Self:
        """Raises UsageError without an attempt in progress."""
        attempt = find_attempt(environment.progress, request.slug, request.language)
        return cls(attempt, environment.problems.load(attempt.slug).meta)

    def started(self, command: RunCommand, level: int | None) -> RunStarted:
        """Raises UsageError for a level still locked."""
        attempt = self.attempt
        levels = project_levels(self.meta, attempt.level_unlocked, level)
        return RunStarted(command, self.meta, attempt, autograded_language(attempt), levels)


def _notices(emit: EventSink) -> ProgressNotice:
    return lambda line: emit(OutputLine(line))


def _shown(result: SubmitResult) -> Iterator[CaseVerdict]:
    """Every graded case, but a mock attempt names no hidden one, not even a failing one."""
    verdicts = result.judgement.verdicts
    return (verdict for verdict in verdicts if verdict.case.visible or not result.is_mock)
