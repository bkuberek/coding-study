"""Judging a runner against the conformance suite's expected outcomes (runners/conformance/)."""

from collections import Counter
from collections.abc import Collection

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import JsonValue
from coding_study.domain.conformance import ExpectedOutcome, ExpectedStatus
from coding_study.domain.judging import CaseVerdict
from coding_study.domain.runs import InvalidOutput, Raised, Returned, Stalled, TimedOut
from coding_study.domain.stress_runs import RUN_ID_SEPARATOR
from coding_study.domain.stress_verdict import StressRunResult, StressVerdict
from coding_study.domain.value_text import json_text, value_text

_STRESS_STATUSES = {
    ExpectedStatus.FAIL: CaseStatus.FAIL,
    ExpectedStatus.ERROR: CaseStatus.ERROR,
    ExpectedStatus.INVALID_OUTPUT: CaseStatus.INVALID,
    ExpectedStatus.TIMEOUT: CaseStatus.TIMEOUT,
    ExpectedStatus.STALLED: CaseStatus.STALLED,
}
MIN_DISTINCT_RECORDS = 2

_STATUS_OUTCOMES = {
    ExpectedStatus.ERROR: Raised,
    ExpectedStatus.INVALID_OUTPUT: InvalidOutput,
    ExpectedStatus.TIMEOUT: TimedOut,
}


def outcome_mismatch(expected: ExpectedOutcome, verdict: CaseVerdict) -> str | None:
    """Why the judged case does not match the expected outcome, or None when it does."""
    got = f"got {verdict.status.value}"
    if expected.status is ExpectedStatus.PASS:
        if verdict.status is not CaseStatus.PASS:
            return f"expected pass, {got}"
        return _stdout_mismatch(expected, verdict)
    if expected.status is ExpectedStatus.LOAD_ERROR:
        return f"expected load_error, but the target loaded ({got})"
    if not isinstance(verdict.outcome, _STATUS_OUTCOMES[expected.status]):
        return f"expected {expected.status.value}, {got}"
    if isinstance(verdict.outcome, Raised):
        return _error_mismatch(expected, verdict.outcome)
    return None


def _stdout_mismatch(expected: ExpectedOutcome, verdict: CaseVerdict) -> str | None:
    outcome = verdict.outcome
    if expected.stdout is None or not isinstance(outcome, Returned):
        return None
    if outcome.stdout == expected.stdout:
        return None
    return f"expected stdout {json_text(expected.stdout)}, got {json_text(outcome.stdout)}"


def _error_mismatch(expected: ExpectedOutcome, outcome: Raised) -> str | None:
    message = outcome.error.message
    if expected.message is not None and message != expected.message:
        return f"expected message {json_text(expected.message)}, got {json_text(message)}"
    if expected.op_index is not None and outcome.op_index != expected.op_index:
        return f"expected op_index {expected.op_index}, got {outcome.op_index}"
    partial = expected.partial_output
    if partial is not None and outcome.partial_output != partial:
        wanted, actual = value_text(list(partial)), value_text(list(outcome.partial_output))
        return f"expected partial_output {wanted}, got {actual}"
    return None


def stress_mismatch(
    expected: ExpectedOutcome, verdict: StressVerdict, restarted_after: Collection[str]
) -> str | None:
    """Why one (stress case, variant) does not match the expected outcome, or None.

    `restarted_after`: the run ids after which the runner asked to be restarted.
    """
    where = f"{verdict.case_id} {verdict.variant}"
    run_ids = {
        RUN_ID_SEPARATOR.join((verdict.case_id, verdict.variant.value, str(run.run)))
        for run in verdict.runs
    }
    if expected.restart_requested and not run_ids & set(restarted_after):
        return f"{where}: expected restart_requested after a run"
    problem = _stress_problem(expected, verdict)
    return f"{where}: {problem}" if problem else None


def _stress_problem(expected: ExpectedOutcome, verdict: StressVerdict) -> str | None:
    if expected.deterministic:
        problem = _determinism_problem(verdict)
        if problem is not None:
            return problem
    runs = verdict.runs
    failed = [run for run in runs if not run.passed]
    if expected.status is ExpectedStatus.PASS:
        allowed = expected.max_failed or 0
        if len(failed) <= allowed:
            return None
        return f"{len(failed)}/{len(runs)} runs failed (at most {allowed}); {_described(failed[0])}"
    wanted = _STRESS_STATUSES.get(expected.status)
    if wanted is None:
        return f"{expected.status} does not apply to stress cases"
    matching = [run for run in failed if run.status is wanted]
    minimum = len(runs) if expected.min_failed is None else expected.min_failed
    if len(matching) < minimum:
        statuses = ", ".join(
            f"{count} {status}"
            for status, count in Counter(run.status.value for run in runs).items()
        )
        return f"expected {expected.status} in at least {minimum}/{len(runs)} runs, got {statuses}"
    if expected.max_failed is not None and len(failed) > expected.max_failed:
        return f"{len(failed)}/{len(runs)} runs failed (at most {expected.max_failed})"
    return next(
        (problem for run in matching if (problem := _run_problem(expected, run)) is not None),
        None,
    )


def _run_problem(expected: ExpectedOutcome, run: StressRunResult) -> str | None:
    """Exact fields of a failing run: message, phase and op index, or a stall's progress."""
    outcome = run.outcome
    where = f"run {run.run}"
    if isinstance(outcome, Raised):
        error_problem = _error_mismatch(expected, outcome)
        if error_problem is not None:
            return f"{where}: {error_problem}"
        phase = outcome.stress.phase.value if outcome.stress else None
        if expected.phase is not None and phase != expected.phase:
            return f"{where}: expected phase {expected.phase}, got {phase}"
    if isinstance(outcome, Stalled) and not any(item.in_op for item in outcome.progress):
        return f"{where}: a stall must name the workers waiting inside an op"
    return None


def _determinism_problem(verdict: StressVerdict) -> str | None:
    """The last run repeats the first run's seed (the suite plans it so)."""
    records = [_comparable(run) for run in verdict.runs]
    if any(record is None for record in records):
        return "every run must complete to compare run records"
    first, repeat = records[0], records[-1]
    if first != repeat:
        return f"seed {verdict.runs[0].seed} gave two different run records"
    distinct = {json_text(record) for record in records[:-1]}
    if len(distinct) < MIN_DISTINCT_RECORDS:
        return f"{len(records) - 1} seeds gave {len(distinct)} distinct run record"
    return None


def _comparable(run: StressRunResult) -> JsonValue:
    if run.record is None:
        return None
    document = run.record.document()
    return {key: value for key, value in document.items() if key not in ("run", "seed")}


def _described(run: StressRunResult) -> str:
    reason = run.reasons[0] if run.reasons else run.status.value
    return f"run {run.run} seed {run.seed}: {reason}"
