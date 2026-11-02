"""The events of `cstudy test --events` and `cstudy submit --events` on a project problem
(docs/specs/cli.md#event-stream).

A stream names its run once the run's options are checked, then passes on each progress notice and
each test, graded case or stress run as the runner reports it: when it starts, and with its
verdict when it ends; each stress case and variant is graded after its last run, with its level.
A mock attempt names no hidden case, stress cases included. Whatever the runner did not report
while it ran, such as cases left not run when restarts ran out, follows when the run ends, in run
order. Then come the diagnostics, each graded level, and the level a submission opened. The command
that writes the stream ends it with the outcome and the exit code, which are the command's own.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.environment import Environment
from coding_study.application.jdk_requirement import require_jdk
from coding_study.application.ports import ProgressNotice
from coding_study.application.project_runs import grading_stress_plan, project_levels
from coding_study.application.project_testing import (
    ProjectTestRequest,
    ProjectTestResult,
    run_project_tests,
)
from coding_study.application.run_events import (
    CaseGraded,
    CaseStarted,
    DiagnosticFound,
    EventSink,
    LevelGraded,
    LevelOpened,
    OutputLine,
    RunCommand,
    RunStarted,
    StressGraded,
    StressRunJudged,
    StressRunStarted,
    SuiteTestReported,
    SuiteTestStarted,
)
from coding_study.application.submit_project import (
    SubmitRequest,
    SubmitResult,
    require_project,
    submit_project,
)
from coding_study.domain.attempts import Attempt, AttemptMode
from coding_study.domain.concurrency import StressVariant
from coding_study.domain.judging import CaseVerdict, Judgement, RunnableCase
from coding_study.domain.problem import Problem, ProblemMeta
from coding_study.domain.project_test_runs import SuiteTestVerdict
from coding_study.domain.stress_runs import PlannedRun, StressSelection
from coding_study.domain.stress_verdict import StressRunResult, StressVerdict


def stream_project_tests(
    environment: Environment, request: ProjectTestRequest, emit: EventSink
) -> ProjectTestResult:
    """Raises as `run_project_tests`: a locked level before any event; a `--case` that names no
    test, or a toolchain that cannot run the suite, after the start."""
    subject = _Subject.find(environment, request)
    emit(subject.started(RunCommand.TEST, request.level, environment.clock.now()))
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
    emit(subject.started(RunCommand.SUBMIT, request.level, environment.clock.now()))
    levels = project_levels(subject.meta, subject.attempt.level_unlocked, request.level)
    language = autograded_language(subject.attempt)
    plan = grading_stress_plan(subject.problem, language, levels.ran_up_to, StressSelection())
    live = _LiveCases(emit, subject, plan)
    result = submit_project(environment, replace(request, listener=live), _notices(emit))
    live.report_the_rest(result.judgement)
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
        problem = environment.problems.load(attempt.slug)
        require_jdk(environment, problem.meta, autograded_language(attempt))
        return cls(attempt, problem)

    def started(self, command: RunCommand, level: int | None, at: datetime) -> RunStarted:
        """Raises UsageError for a level still locked."""
        attempt = self.attempt
        levels = project_levels(self.meta, attempt.level_unlocked, level)
        return RunStarted(command, self.meta, attempt, autograded_language(attempt), levels, at)


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
    """Reports each graded case and stress run as the runner reports it, grades each stress case
    and variant right after its last run, but names no hidden case of a mock attempt, stress
    cases included; and remembers what it reported."""

    def __init__(self, emit: EventSink, subject: _Subject, plan: Sequence[PlannedRun]) -> None:
        self._emit = emit
        self._levels = {case.id: case.level for case in subject.problem.cases}
        self._mock = subject.attempt.mode is AttemptMode.MOCK
        self._judged: set[str] = set()
        self._slots: dict[_StressSlot, list[PlannedRun]] = {}
        for planned in plan:
            self._slots.setdefault(_slot(planned), []).append(planned)
        self._runs: dict[_StressSlot, dict[int, StressRunResult]] = {}
        self._graded: set[_StressSlot] = set()

    def case_started(self, case: RunnableCase) -> None:
        if self._shown(case):
            self._emit(CaseStarted(case, self._levels.get(case.id)))

    def case_judged(self, verdict: CaseVerdict) -> None:
        case = verdict.case
        self._judged.add(case.id)
        if self._shown(case):
            self._emit(CaseGraded(verdict, self._levels.get(case.id)))

    def stress_run_started(self, planned: PlannedRun) -> None:
        if not self._mock:
            self._emit(StressRunStarted(planned, planned.case.level))

    def stress_run_judged(self, planned: PlannedRun, result: StressRunResult) -> None:
        slot = _slot(planned)
        judged = self._runs.setdefault(slot, {})
        judged[planned.run] = result
        if not self._mock:
            self._emit(StressRunJudged(planned, result, planned.case.level))
        runs = self._slots.get(slot, [])
        if len(judged) == len(runs):
            first = runs[0]
            ordered = tuple(judged[run.run] for run in runs)
            self._grade(StressVerdict(first.case, first.variant, ordered, first.deadline_ms))

    def report_the_rest(self, judgement: Judgement) -> None:
        """What the runner did not report while it ran, as the grading's judgement holds it: such
        as cases and runs left not run when restarts ran out."""
        for verdict in judgement.verdicts:
            if verdict.case.id not in self._judged:
                self.case_judged(verdict)
        for stress in judgement.stress:
            slot = (stress.case_id, stress.variant)
            if slot in self._graded:
                continue
            planned = {run.run: run for run in self._slots.get(slot, [])}
            judged = self._runs.get(slot, {})
            for run in stress.runs:
                if run.run not in judged and run.run in planned:
                    self.stress_run_judged(planned[run.run], run)
            if slot not in self._graded:
                self._grade(stress)

    def _grade(self, verdict: StressVerdict) -> None:
        self._graded.add((verdict.case_id, verdict.variant))
        if not self._mock:
            self._emit(StressGraded(verdict, verdict.case.level))

    def _shown(self, case: RunnableCase) -> bool:
        return case.visible or not self._mock


type _StressSlot = tuple[str, StressVariant]


def _slot(planned: PlannedRun) -> _StressSlot:
    return (planned.case.id, planned.variant)


def _notices(emit: EventSink) -> ProgressNotice:
    return lambda line: emit(OutputLine(line))
