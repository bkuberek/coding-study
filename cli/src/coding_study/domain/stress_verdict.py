"""Verdicts of stress cases over N runs (docs/specs/problem-format.md#evaluating-a-run-and-a-case).

A run fails on a runner status (error, invalid output, stall, hang guard), a `final.expected`
mismatch, or any failing invariant. A (stress case, variant) passes only if every run passes;
otherwise it takes the status of its first failing run. A correct implementation satisfies every
invariant on every schedule, so one failing run is a real bug.
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from statistics import median

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected
from coding_study.domain.comparators import Comparator
from coding_study.domain.concurrency import StressVariant
from coding_study.domain.invariants import InvariantContext, StressChecker, invariant_failures
from coding_study.domain.runs import (
    CaseOutcome,
    Crashed,
    InvalidOutput,
    JobReport,
    NotRun,
    Raised,
    Returned,
    Stalled,
    StressCompleted,
    StressFailure,
    StressPhase,
    TimedOut,
    WorkerProgress,
)
from coding_study.domain.stress_record import StressRecord, stress_record
from coding_study.domain.stress_runs import PlannedRun, WorkerScript

SHOWN_FAILING_RUNS = 3
SHOWN_REASONS = 3
NANOSECONDS_PER_MILLISECOND = 1_000_000


@dataclass(frozen=True, slots=True)
class StressRunResult:
    run: int
    seed: int
    status: CaseStatus
    reasons: tuple[str, ...] = ()
    """Why the run failed; the first few invariant reasons, or the runner status."""
    duration_ns: int | None = None
    """From gate open until the last worker finished (or the failure or deadline)."""
    record: StressRecord | None = None
    """Only for runs that completed."""
    stdout: str = ""
    outcome: CaseOutcome | None = None
    """What the runner reported, for the conformance suite's checks."""

    @property
    def passed(self) -> bool:
        return self.status is CaseStatus.PASS


@dataclass(frozen=True, slots=True)
class StressVerdict:
    case: Case
    variant: StressVariant
    runs: tuple[StressRunResult, ...]
    deadline_ms: int

    @property
    def case_id(self) -> str:
        return self.case.id

    @property
    def status(self) -> CaseStatus:
        failed = next((run for run in self.runs if not run.passed), None)
        return CaseStatus.PASS if failed is None else failed.status

    @property
    def runs_passed(self) -> int:
        return sum(1 for run in self.runs if run.passed)

    @property
    def failures(self) -> tuple[StressRunResult, ...]:
        """The first few failing runs, as `cstudy test` lists them."""
        return tuple(run for run in self.runs if not run.passed)[:SHOWN_FAILING_RUNS]

    @property
    def failed_runs(self) -> int:
        return len(self.runs) - self.runs_passed

    @property
    def median_ms(self) -> float | None:
        durations = self._durations()
        return median(durations) / NANOSECONDS_PER_MILLISECOND if durations else None

    @property
    def slowest_share(self) -> float | None:
        """The slowest run as a share of the deadline (D6; ready needs at most 0.25)."""
        durations = self._durations()
        if not durations:
            return None
        return max(durations) / (self.deadline_ms * NANOSECONDS_PER_MILLISECOND)

    def _durations(self) -> list[int]:
        return [run.duration_ns for run in self.runs if run.duration_ns is not None]


@dataclass(frozen=True, slots=True)
class StressJudging:
    comparator: Comparator
    """The problem's `ops` comparator, for `final.expected`."""
    checker: StressChecker | None = None


def judge_stress(
    planned: Sequence[PlannedRun], job: JobReport, judging: StressJudging
) -> tuple[StressVerdict, ...]:
    """One verdict per (stress case, variant), in plan order."""
    outcomes: Mapping[str, CaseOutcome] = {report.case_id: report.outcome for report in job.cases}
    groups: dict[tuple[str, StressVariant], list[PlannedRun]] = {}
    for run in planned:
        groups.setdefault((run.case.id, run.variant), []).append(run)
    return tuple(
        StressVerdict(
            runs[0].case,
            variant,
            tuple(judge_run(run, outcomes.get(run.run_id, _MISSING), judging) for run in runs),
            runs[0].deadline_ms,
        )
        for (_, variant), runs in groups.items()
    )


_MISSING = NotRun("the runner reported no result")


def judge_run(planned: PlannedRun, outcome: CaseOutcome, judging: StressJudging) -> StressRunResult:
    if not isinstance(outcome, StressCompleted):
        status, reason, duration_ns = _runner_failure(planned, outcome)
        stdout = outcome.stdout if isinstance(outcome, Raised | InvalidOutput | Stalled) else ""
        return StressRunResult(
            planned.run,
            planned.seed,
            status,
            (reason,),
            duration_ns,
            stdout=stdout,
            outcome=outcome,
        )
    record = stress_record(planned, outcome)
    reasons = [*_final_mismatch(planned, outcome, judging.comparator)]
    context = InvariantContext(planned.scenario.document, judging.checker)
    reasons += invariant_failures(planned.scenario.invariants, record, context)
    status = CaseStatus.FAIL if reasons else CaseStatus.PASS
    return StressRunResult(
        planned.run,
        planned.seed,
        status,
        tuple(reasons[:SHOWN_REASONS]),
        outcome.duration_ns,
        record,
        outcome.stdout,
        outcome,
    )


def _final_mismatch(
    planned: PlannedRun, outcome: StressCompleted, comparator: Comparator
) -> Iterator[str]:
    final = planned.scenario.final
    if final is None or final.expected is None:
        return
    mismatch = comparator.compare(
        Expected(list(final.expected)), list(outcome.final), final.sequence
    )
    if mismatch is not None:
        yield f"final: {mismatch.detail or 'unexpected outputs'}"


def _runner_failure(
    planned: PlannedRun, outcome: CaseOutcome
) -> tuple[CaseStatus, str, int | None]:
    match outcome:
        case Raised(error=error, duration_ns=duration_ns, stress=stress):
            text = f"{error.type}: {error.message}" if error.message else error.type
            return CaseStatus.ERROR, f"{_where(planned, stress)}{text}", duration_ns
        case InvalidOutput(reason=reason, duration_ns=duration_ns, stress=stress):
            return CaseStatus.INVALID, f"{_where(planned, stress)}{reason}", duration_ns
        case Stalled(progress=progress, duration_ns=duration_ns):
            return CaseStatus.STALLED, progress_text(planned, progress), None
        case TimedOut(limit_ms=limit_ms):
            return CaseStatus.TIMEOUT, f"hang guard expired after {limit_ms} ms", None
        case Crashed(exit_code=exit_code):
            return CaseStatus.ERROR, f"runner exited with code {exit_code}", None
        case NotRun(reason=reason):
            return CaseStatus.NOT_RUN, reason, None
        case Returned() | StressCompleted():
            return CaseStatus.ERROR, "the runner reported no stress run result", None


def _where(planned: PlannedRun, stress: StressFailure | None) -> str:
    """`consumer[1] op 311 (take): `; the setup and final phases name themselves."""
    if stress is None:
        return ""
    match stress.phase:
        case StressPhase.WORKER if stress.worker is not None and stress.worker < len(
            planned.workers
        ):
            script = planned.workers[stress.worker]
            return f"{script.label} op {stress.op_index} ({_op(script.ops, stress.op_index)}): "
        case StressPhase.SETUP:
            ops = planned.scenario.setup.ops
            return f"setup op {stress.op_index} ({_op(ops, stress.op_index)}): "
        case StressPhase.FINAL:
            final = planned.scenario.final
            ops = final.ops if final else ()
            return f"final op {stress.op_index} ({_op(ops, stress.op_index)}): "
        case _:
            return f"worker {stress.worker} op {stress.op_index}: "


def _op(ops: Sequence[str], index: int) -> str:
    return ops[index] if 0 <= index < len(ops) else "?"


def progress_text(planned: PlannedRun, progress: Sequence[WorkerProgress]) -> str:
    """Where the unfinished workers were: `producer[0] in put (op 704 of 1000) · consumer[0..2]
    in take`. Consecutive workers of one group in the same place share one entry."""
    places = [
        (planned.workers[item.worker], item)
        for item in sorted(progress, key=lambda item: item.worker)
        if 0 <= item.worker < len(planned.workers)
    ]
    if not places:
        return "no worker reported progress"
    runs: list[list[tuple[WorkerScript, WorkerProgress]]] = []
    for place in places:
        previous = runs[-1][-1] if runs else None
        if previous is not None and _same_place(previous, place):
            runs[-1].append(place)
        else:
            runs.append([place])
    return " · ".join(_place_text(run) for run in runs)


def _same_place(
    earlier: tuple[WorkerScript, WorkerProgress], later: tuple[WorkerScript, WorkerProgress]
) -> bool:
    (script, progress), (next_script, next_progress) = earlier, later
    return (
        script.group == next_script.group
        and next_script.index == script.index + 1
        and _state(script, progress) == _state(next_script, next_progress)
    )


def _state(script: WorkerScript, progress: WorkerProgress) -> str:
    op = _op(script.ops, progress.completed)
    return f"in {op}" if progress.in_op else f"before {op}"


def _place_text(run: list[tuple[WorkerScript, WorkerProgress]]) -> str:
    script, progress = run[0]
    if len(run) == 1:
        position = f"op {progress.completed} of {len(script.ops)}"
        return f"{script.label} {_state(script, progress)} ({position})"
    last = run[-1][0]
    return f"{script.group}[{script.index}..{last.index}] {_state(script, progress)}"
