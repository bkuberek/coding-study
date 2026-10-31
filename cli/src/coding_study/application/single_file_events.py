"""The events of `cstudy test --events` on a problem that is not a project: function, design,
progressive and concurrent, the debugging track's included (docs/specs/cli.md#event-stream).

A stream names its run once its options are checked, with what the run will report. Then come
progress notices, the build of a language that has one, and each case, oracle input and stress run
as the runner reports it: when it starts, and judged when it ends. Each stress case and variant is
graded right after its last run. Whatever the runner did not report while it ran, such as cases
left not run when restarts ran out, follows when the run ends, in run order. Then come the cases
the time limits turned into `tle`, the diagnostics, the level the run opened, and with `--perf`
the short bench. The command that writes the stream ends it with the outcome and the exit code,
which are the command's own.
"""

from collections.abc import Iterable
from dataclasses import replace

from coding_study.application.environment import Environment
from coding_study.application.ports import ProgressNotice
from coding_study.application.run_bench import BenchResult
from coding_study.application.run_events import (
    BuildEnded,
    CaseGraded,
    CaseRevised,
    CaseStarted,
    DiagnosticFound,
    EventSink,
    LevelOpened,
    OutputLine,
    PerfChecked,
    PlannedCases,
    RunCommand,
    RunStarted,
    StressGraded,
    StressPlan,
    StressRunJudged,
    StressRunStarted,
)
from coding_study.application.run_tests import (
    RunTestsPlan,
    RunTestsRequest,
    RunTestsResult,
    perf_check,
    plan_tests,
    run_planned_tests,
)
from coding_study.application.stress_judging import sequential_cases
from coding_study.application.submit_project import OpenedLevel, level_method_texts
from coding_study.domain import layout
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import GeneratedInput
from coding_study.domain.concurrency import StressVariant
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.stress_runs import PlannedRun
from coding_study.domain.stress_verdict import StressRunResult, StressVerdict

type _StressSlot = tuple[str, StressVariant]
"""A stress case and variant: one verdict."""


def stream_tests(
    environment: Environment, request: RunTestsRequest, emit: EventSink
) -> RunTestsResult:
    """Raises as `run_tests`: a usage error in the options before any event; an error that stops
    the run after the start."""
    plan = plan_tests(environment, request)
    emit(_started(plan, environment))
    live = _LiveRun(emit, plan)
    result = run_planned_tests(environment, replace(plan, listener=live), _notices(emit))
    live.report_the_rest(result)
    live.revise(result.judgement.verdicts if result.judgement else ())
    for diagnostic in result.diagnostics:
        emit(DiagnosticFound(diagnostic))
    opened = opened_level(result)
    if opened is not None:
        emit(LevelOpened(opened))
    return result


def stream_perf(
    environment: Environment, result: RunTestsResult, emit: EventSink
) -> BenchResult | None:
    """`--perf`: the short bench after a pass of every case, its notices as `output`; None when
    it did not run."""
    bench = perf_check(environment, result, _notices(emit))
    if bench is not None:
        emit(PerfChecked(bench))
    return bench


def opened_level(result: RunTestsResult) -> OpenedLevel | None:
    """The level a run of a progressive problem opened, which has no generated test files."""
    levels = result.levels
    if levels is None or not levels.newly_unlocked:
        return None
    level = levels.unlocked
    return OpenedLevel(
        level=level,
        title=levels.progress.title(level),
        methods=level_method_texts(result.meta, level, result.language),
        tests=None,
        statement=layout.statement_path(result.meta.slug),
    )


def _started(plan: RunTestsPlan, environment: Environment) -> RunStarted:
    return RunStarted(
        RunCommand.TEST,
        plan.meta,
        plan.attempt,
        plan.language,
        plan.levels,
        environment.clock.now(),
        plan.time_limit,
        _planned(plan),
    )


def _planned(plan: RunTestsPlan) -> PlannedCases:
    """The counts the report's header prints: a generated case is neither visible nor hidden."""
    cases = sequential_cases(plan.selected)
    generated = sum(1 for case in cases if isinstance(case.input, GeneratedInput))
    visible = sum(1 for case in cases if case.visible)
    return PlannedCases(
        cases=len(cases),
        visible=visible,
        hidden=len(cases) - visible - generated,
        generated=generated,
        oracle_inputs=len(plan.oracle.inputs) if plan.oracle else 0,
        stress=_stress_plan(plan.stress_plan) if plan.meta.concurrency else None,
    )


def _stress_plan(planned: tuple[PlannedRun, ...]) -> StressPlan:
    slots = {(run.case.id, run.variant) for run in planned}
    return StressPlan(
        cases=len({case_id for case_id, _ in slots}),
        variants=len({variant for _, variant in slots}),
        runs=len(planned) // len(slots) if slots else 0,
    )


class _LiveRun:
    """Reports each case, oracle input and stress run as the runner reports it, grades each
    stress case and variant after its last run, and remembers what it reported."""

    def __init__(self, emit: EventSink, plan: RunTestsPlan) -> None:
        self._emit = emit
        self._levels = {case.id: case.level for case in plan.problem.cases}
        self._oracle = {found.case_id: found for found in plan.oracle.inputs} if plan.oracle else {}
        self._statuses: dict[str, CaseStatus] = {}
        self._slots: dict[_StressSlot, list[PlannedRun]] = {}
        for planned in plan.stress_plan:
            self._slots.setdefault(_slot(planned), []).append(planned)
        self._judged: dict[_StressSlot, dict[int, StressRunResult]] = {}

    def build_ended(self, seconds: float, note: str | None) -> None:
        self._emit(BuildEnded(seconds, note))

    def case_started(self, case: RunnableCase) -> None:
        self._emit(CaseStarted(case, self._levels.get(case.id), self._oracle.get(case.id)))

    def case_judged(self, verdict: CaseVerdict) -> None:
        case_id = verdict.case.id
        self._statuses[case_id] = verdict.status
        self._emit(CaseGraded(verdict, self._levels.get(case_id), self._oracle.get(case_id)))

    def stress_run_started(self, planned: PlannedRun) -> None:
        self._emit(StressRunStarted(planned))

    def stress_run_judged(self, planned: PlannedRun, result: StressRunResult) -> None:
        slot = _slot(planned)
        judged = self._judged.setdefault(slot, {})
        judged[planned.run] = result
        self._emit(StressRunJudged(planned, result))
        runs = self._slots[slot]
        if len(judged) == len(runs):
            first = runs[0]
            ordered = tuple(judged[run.run] for run in runs)
            verdict = StressVerdict(first.case, first.variant, ordered, first.deadline_ms)
            self._emit(StressGraded(verdict))

    def report_the_rest(self, result: RunTestsResult) -> None:
        """What the runner did not report while it ran, as the run's judgement holds it."""
        judgement = result.judgement
        if judgement is None or judgement.load_error is not None:
            return
        for verdict in judgement.verdicts:
            if verdict.case.id not in self._statuses:
                self.case_judged(_before_time_limits(verdict))
        for stress in judgement.stress:
            slot = (stress.case_id, stress.variant)
            planned = {run.run: run for run in self._slots[slot]}
            judged = self._judged.get(slot, {})
            for run in stress.runs:
                if run.run not in judged:
                    self.stress_run_judged(planned[run.run], run)

    def revise(self, verdicts: Iterable[CaseVerdict]) -> None:
        """The cases whose verdict the time limits changed, once they are known."""
        for verdict in verdicts:
            if verdict.status is not self._statuses.get(verdict.case.id, verdict.status):
                self._emit(CaseRevised(verdict, self._levels.get(verdict.case.id)))


def _before_time_limits(verdict: CaseVerdict) -> CaseVerdict:
    """A case's verdict as the comparator gave it: a time limit is a revision."""
    if verdict.status is not CaseStatus.TLE:
        return verdict
    return replace(verdict, status=CaseStatus.PASS, time_limit=None)


def _slot(planned: PlannedRun) -> _StressSlot:
    return (planned.case.id, planned.variant)


def _notices(emit: EventSink) -> ProgressNotice:
    return lambda line: emit(OutputLine(line))
