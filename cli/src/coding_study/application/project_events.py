"""The events of `cstudy test --events` and `cstudy submit --events` on a project problem
(docs/specs/cli.md#event-stream).

A stream names its run once the run's options are checked, then passes on each progress notice and
each test or graded case as the runner reports it: when it starts, and with its verdict when it
ends. A mock attempt names no hidden case. Whatever the runner did not report while it ran, such as
cases left not run when restarts ran out, follows when the run ends, in run order. Then come the
diagnostics, each graded level, and the level a submission opened. The command that writes the
stream ends it with the outcome and the exit code, which are the command's own.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
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
from coding_study.domain.attempts import Attempt, AttemptMode
from coding_study.domain.diagnostics import Diagnostic
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.levels import LevelRun
from coding_study.domain.problem import Language, Problem, ProblemMeta
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
class SuiteTestStarted:
    """The runner started one test of the native suite (`cstudy test`)."""

    test_id: str


@dataclass(frozen=True, slots=True)
class SuiteTestReported:
    """One test of the native suite ended (`cstudy test`)."""

    verdict: SuiteTestVerdict


@dataclass(frozen=True, slots=True)
class CaseStarted:
    """The runner started one graded case (`cstudy submit`)."""

    case: RunnableCase
    level: int | None


@dataclass(frozen=True, slots=True)
class CaseGraded:
    """One graded case ended and was judged (`cstudy submit`)."""

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
    | SuiteTestStarted
    | SuiteTestReported
    | CaseStarted
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
    live = _LiveTests(emit)
    result = run_project_tests(environment, replace(request, listener=live), _notices(emit))
    live.report_the_rest(result.verdicts)
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
    live = _LiveCases(emit, subject)
    result = submit_project(environment, replace(request, listener=live), _notices(emit))
    live.report_the_rest(result.judgement.verdicts)
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
    problem: Problem

    @property
    def meta(self) -> ProblemMeta:
        return self.problem.meta

    @classmethod
    def find(cls, environment: Environment, request: ProjectTestRequest | SubmitRequest) -> Self:
        """Raises UsageError without an attempt in progress."""
        attempt = find_attempt(environment.progress, request.slug, request.language)
        return cls(attempt, environment.problems.load(attempt.slug))

    def started(self, command: RunCommand, level: int | None) -> RunStarted:
        """Raises UsageError for a level still locked."""
        attempt = self.attempt
        levels = project_levels(self.meta, attempt.level_unlocked, level)
        return RunStarted(command, self.meta, attempt, autograded_language(attempt), levels)


class _LiveTests:
    """Reports each test as the runner reports it, and remembers which it reported."""

    def __init__(self, emit: EventSink) -> None:
        self._emit = emit
        self._reported: set[str] = set()

    def test_started(self, test_id: str) -> None:
        self._emit(SuiteTestStarted(test_id))

    def test_judged(self, verdict: SuiteTestVerdict) -> None:
        self._reported.add(verdict.test.test_id)
        self._emit(SuiteTestReported(verdict))

    def report_the_rest(self, verdicts: Iterable[SuiteTestVerdict]) -> None:
        for verdict in verdicts:
            if verdict.test.test_id not in self._reported:
                self.test_judged(verdict)


class _LiveCases:
    """Reports each graded case as the runner reports it, but no hidden one of a mock attempt,
    and remembers which it reported."""

    def __init__(self, emit: EventSink, subject: _Subject) -> None:
        self._emit = emit
        self._levels = {case.id: case.level for case in subject.problem.cases}
        self._mock = subject.attempt.mode is AttemptMode.MOCK
        self._judged: set[str] = set()

    def case_started(self, case: RunnableCase) -> None:
        if self._shown(case):
            self._emit(CaseStarted(case, self._levels.get(case.id)))

    def case_judged(self, verdict: CaseVerdict) -> None:
        case = verdict.case
        self._judged.add(case.id)
        if self._shown(case):
            self._emit(CaseGraded(verdict, self._levels.get(case.id)))

    def report_the_rest(self, verdicts: Iterable[CaseVerdict]) -> None:
        for verdict in verdicts:
            if verdict.case.id not in self._judged:
                self.case_judged(verdict)

    def _shown(self, case: RunnableCase) -> bool:
        return case.visible or not self._mock


def _notices(emit: EventSink) -> ProgressNotice:
    return lambda line: emit(OutputLine(line))
