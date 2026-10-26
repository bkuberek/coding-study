"""Per-case verdicts from a runner report (docs/specs/cli.md#cstudy-test).

The runner reports what the code did; judging decides whether that was right, using the problem's
comparator against expected values the runner never saw.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected, GeneratedInput
from coding_study.domain.comparators import Comparator, Mismatch
from coding_study.domain.runs import (
    CaseOutcome,
    Crashed,
    InvalidOutput,
    JobReport,
    NotRun,
    Raised,
    Returned,
    RunInput,
    Stalled,
    StressCompleted,
    TimedOut,
    UserError,
)
from coding_study.domain.stress import StressScenario
from coding_study.domain.stress_verdict import StressVerdict
from coding_study.domain.time_limits import (
    NANOSECONDS_PER_MILLISECOND,
    CaseLimit,
    TimeLimits,
)
from coding_study.domain.value_text import value_text


@dataclass(frozen=True, slots=True)
class RunnableCase:
    """A case ready to send to a runner: generated inputs are already materialized."""

    id: str
    input: RunInput
    expected: Expected | None
    """None only for checker problems without a displayed answer."""
    visible: bool = False
    generated: bool = False
    hang_guard_ms: int | None = None
    note: str | None = None


def concrete_case(case: Case) -> RunnableCase:
    """A hand-written case; generated cases need generator.py first."""
    if isinstance(case.input, GeneratedInput):
        raise ValueError(f'case "{case.id}" is generated; materialize it with its generator')
    if isinstance(case.input, StressScenario):
        raise ValueError(f'case "{case.id}" is a stress case; plan its runs with stress_runs')
    return RunnableCase(
        id=case.id,
        input=case.input,
        expected=case.expected,
        visible=case.visible,
        hang_guard_ms=case.hang_guard_ms,
        note=case.note,
    )


@dataclass(frozen=True, slots=True)
class CaseVerdict:
    case: RunnableCase
    status: CaseStatus
    outcome: CaseOutcome
    mismatch: Mismatch | None = None
    """Why the output was rejected; only for FAIL."""
    time_limit: CaseLimit | None = None
    """The limit the call exceeded; only for TLE."""

    @property
    def duration_ns(self) -> int | None:
        """The runner's measurement of the call, when the call finished."""
        if isinstance(self.outcome, Returned | Raised | InvalidOutput):
            return self.outcome.duration_ns
        return None


@dataclass(frozen=True, slots=True)
class Tally:
    """The counts stored in `test_runs` (docs/specs/progress-and-scheduling.md#schema)."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    """Wrong answers and invalid outputs."""
    errored: int = 0
    """Exceptions, crashes, cases not run, and every case of code that did not build or load."""
    timed_out: int = 0
    tle: int = 0

    @property
    def all_passed(self) -> bool:
        return self.passed == self.total


_TALLY_FIELDS = {
    CaseStatus.PASS: "passed",
    CaseStatus.FAIL: "failed",
    CaseStatus.INVALID: "failed",
    CaseStatus.ERROR: "errored",
    CaseStatus.NOT_RUN: "errored",
    CaseStatus.TIMEOUT: "timed_out",
    CaseStatus.STALLED: "timed_out",
    CaseStatus.TLE: "tle",
}
_STRESS_TALLY_FIELDS = {**_TALLY_FIELDS, CaseStatus.INVALID: "errored"}
"""Each (stress case, variant) counts as one case; `INVALID` counts as errored there."""


@dataclass(frozen=True, slots=True)
class Judgement:
    """Verdicts in case order, or the load error that kept every case from running."""

    case_count: int
    """Sequential cases plus one per (stress case, variant)."""
    verdicts: tuple[CaseVerdict, ...] = ()
    load_error: UserError | None = None
    stress: tuple[StressVerdict, ...] = ()
    """Concurrent problems: one verdict per (stress case, variant)."""

    @property
    def passed(self) -> bool:
        return self.load_error is None and self.count(CaseStatus.PASS) == self.case_count

    def count(self, status: CaseStatus) -> int:
        statuses = [
            *(verdict.status for verdict in self.verdicts),
            *(verdict.status for verdict in self.stress),
        ]
        return statuses.count(status)

    def tally(self) -> Tally:
        if self.load_error is not None:
            return failed_to_run(self.case_count)
        counts = dict.fromkeys(_TALLY_FIELDS.values(), 0)
        for verdict in self.verdicts:
            counts[_TALLY_FIELDS[verdict.status]] += 1
        for stress in self.stress:
            counts[_STRESS_TALLY_FIELDS[stress.status]] += 1
        return Tally(total=self.case_count, **counts)


def with_stress(judgement: Judgement, stress: Sequence[StressVerdict]) -> Judgement:
    """Adds the stress verdicts of a concurrent problem; a load error keeps every case unrun."""
    case_count = judgement.case_count + len(stress)
    if judgement.load_error is not None:
        return replace(judgement, case_count=case_count)
    return replace(judgement, case_count=case_count, stress=tuple(stress))


def with_oracle(judgement: Judgement, oracle: Judgement) -> Judgement:
    """Adds the verdicts of `cstudy test --stress` oracle inputs, judged from the same job."""
    case_count = judgement.case_count + oracle.case_count
    if judgement.load_error is not None:
        return replace(judgement, case_count=case_count)
    return replace(judgement, case_count=case_count, verdicts=judgement.verdicts + oracle.verdicts)


def failed_to_run(case_count: int) -> Tally:
    """Code that did not build or load: every case counts as errored."""
    return Tally(total=case_count, errored=case_count)


def outcome_summary(outcome: CaseOutcome) -> str:
    """One line describing what the code did, for reports about reference code."""
    match outcome:
        case Returned(output=output):
            return f"returned {value_text(output)}"
        case Raised(error=error, op_index=op_index):
            where = f" at op {op_index}" if op_index is not None else ""
            return f"{error.type}: {error.message}{where}"
        case InvalidOutput(reason=reason):
            return f"invalid output: {reason}"
        case TimedOut(limit_ms=limit_ms):
            return f"timed out after {limit_ms} ms"
        case Crashed(exit_code=exit_code):
            return f"runner crashed with exit code {exit_code}"
        case NotRun(reason=reason):
            return f"not run: {reason}"
        case StressCompleted():
            return "completed a stress run"
        case Stalled(progress=progress):
            return f"stalled with {len(progress)} unfinished workers"


SUMMARY_VALUE_LIMIT = 80


def verdict_summary(verdict: CaseVerdict) -> str:
    """One line per case for reports about reference code, e.g. `h1 FAIL: expected 1, got 2`."""
    head = f"{verdict.case.id} {verdict.status.value}"
    outcome = verdict.outcome
    if verdict.status is CaseStatus.PASS:
        return head
    if isinstance(outcome, Returned):
        expected = verdict.case.expected
        wanted = value_text(expected.value, SUMMARY_VALUE_LIMIT) if expected else "a valid answer"
        detail = f"expected {wanted}, got {value_text(outcome.output, SUMMARY_VALUE_LIMIT)}"
        reason = verdict.mismatch.detail if verdict.mismatch else None
        return f"{head}: {detail}" + (f" ({reason})" if reason else "")
    return f"{head}: {outcome_summary(outcome)}"


def judge(cases: Sequence[RunnableCase], job: JobReport, comparator: Comparator) -> Judgement:
    if job.load_error is not None:
        return Judgement(len(cases), load_error=job.load_error)
    outcomes = {report.case_id: report.outcome for report in job.cases}
    verdicts = (_verdict(case, outcomes.get(case.id, _MISSING), comparator) for case in cases)
    return Judgement(len(cases), tuple(verdicts))


def with_time_limits(judgement: Judgement, limits: TimeLimits) -> Judgement:
    """Passing cases whose call took longer than their limit become TLE."""
    verdicts = tuple(_timed(verdict, limits) for verdict in judgement.verdicts)
    return replace(judgement, verdicts=verdicts)


def _timed(verdict: CaseVerdict, limits: TimeLimits) -> CaseVerdict:
    limit = limits.for_case(verdict.case.id)
    duration_ns = verdict.duration_ns
    if verdict.status is not CaseStatus.PASS or limit is None or duration_ns is None:
        return verdict
    if duration_ns <= limit.ms * NANOSECONDS_PER_MILLISECOND:
        return verdict
    return replace(verdict, status=CaseStatus.TLE, time_limit=limit)


_MISSING = NotRun("the runner reported no result")


def _verdict(case: RunnableCase, outcome: CaseOutcome, comparator: Comparator) -> CaseVerdict:
    match outcome:
        case Returned(output=output):
            mismatch = comparator.compare(case.expected, output, case.input)
            status = CaseStatus.PASS if mismatch is None else CaseStatus.FAIL
            return CaseVerdict(case, status, outcome, mismatch)
        case Raised() | Crashed() | StressCompleted():
            return CaseVerdict(case, CaseStatus.ERROR, outcome)
        case InvalidOutput():
            return CaseVerdict(case, CaseStatus.INVALID, outcome)
        case TimedOut():
            return CaseVerdict(case, CaseStatus.TIMEOUT, outcome)
        case NotRun():
            return CaseVerdict(case, CaseStatus.NOT_RUN, outcome)
        case Stalled():
            return CaseVerdict(case, CaseStatus.STALLED, outcome)
