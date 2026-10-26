"""`cstudy test --json`: one JSON document per run (docs/specs/cli.md#json-output).

Every case is listed, passing hidden ones included; a case that did not pass adds what the text
report shows for it. Statuses are the text statuses in lower case, `NOT RUN` as `not_run`.
"""

from collections.abc import Sequence
from datetime import timedelta

from coding_study.application.language_runs import CodeRun
from coding_study.application.run_tests import OracleStress, RunTestsResult
from coding_study.domain.cases import FunctionInput, JsonValue, OperationSequence
from coding_study.domain.judging import CaseStatus, CaseVerdict, Tally, outcome_summary
from coding_study.domain.levels import LevelRun
from coding_study.domain.runs import (
    Crashed,
    InvalidOutput,
    NotRun,
    Raised,
    Returned,
    RunInput,
    Stalled,
    StressCompleted,
    TimedOut,
    UserError,
)
from coding_study.domain.stress_verdict import StressRunResult, StressVerdict

DECIMALS = 3


def run_document(result: RunTestsResult, exit_code: int) -> dict[str, JsonValue]:
    judgement = result.judgement
    load_error = judgement.load_error if judgement else None
    verdicts = judgement.verdicts if judgement else ()
    oracle_ids = result.oracle.case_ids if result.oracle else frozenset[str]()
    return {
        "slug": result.meta.slug,
        "language": result.language.value,
        "attempt_id": result.attempt.id,
        "outcome": _outcome(result),
        "exit_code": exit_code,
        "every_case": result.every_case,
        "comparator": result.comparator.label,
        "time_limit": str(result.time_limits.limit) if result.time_limits else None,
        "timer": _timer(result),
        "levels": _levels(result.levels),
        "build": _build(result.code_run),
        "load_error": _error(load_error) if load_error else None,
        "cases": [_case(verdict) for verdict in verdicts if verdict.case.id not in oracle_ids],
        "oracle": _oracle(result.oracle, verdicts),
        "stress": [_stress(verdict) for verdict in judgement.stress] if judgement else [],
        "tally": _tally(result.tally),
        "duration_s": round(result.duration_seconds, DECIMALS),
    }


def operations_up_to(run_input: RunInput, op_index: int | None) -> RunInput:
    """Class kinds that failed at op k show the operations up to and including k."""
    if isinstance(run_input, FunctionInput) or op_index is None:
        return run_input
    return OperationSequence(run_input.ops[: op_index + 1], run_input.args[: op_index + 1])


def status_value(status: CaseStatus) -> str:
    return status.name.lower()


def _outcome(result: RunTestsResult) -> str:
    judgement = result.judgement
    if judgement is None:
        return "build_failed"
    if judgement.load_error is not None:
        return "load_failed"
    return "passed" if judgement.passed else "failed"


def _timer(result: RunTestsResult) -> JsonValue:
    limit_s = result.attempt.time_limit_s
    if limit_s is None:
        return None
    elapsed = result.attempt.solve_time(result.ran_at) // timedelta(seconds=1)
    return {"elapsed_s": elapsed, "limit_s": limit_s}


def _levels(levels: LevelRun | None) -> JsonValue:
    if levels is None:
        return None
    return {
        "ran_up_to": levels.ran_up_to,
        "last": levels.progress.last,
        "unlocked": levels.unlocked,
        "newly_unlocked": levels.newly_unlocked,
    }


def _build(code_run: CodeRun) -> JsonValue:
    failure = code_run.build_failure
    return {
        "seconds": round(code_run.build_seconds, DECIMALS),
        "note": code_run.build_note,
        "diagnostics": list(failure.diagnostics) if failure else [],
    }


def _tally(tally: Tally) -> JsonValue:
    return {
        "total": tally.total,
        "passed": tally.passed,
        "failed": tally.failed,
        "errored": tally.errored,
        "timed_out": tally.timed_out,
        "tle": tally.tle,
    }


def _case(verdict: CaseVerdict) -> dict[str, JsonValue]:
    case = verdict.case
    entry: dict[str, JsonValue] = {
        "id": case.id,
        "visible": case.visible,
        "generated": case.generated,
        "status": status_value(verdict.status),
        "duration_ns": verdict.duration_ns,
    }
    if verdict.status is CaseStatus.PASS:
        return entry
    limit = verdict.time_limit
    if verdict.status is CaseStatus.TLE and limit is not None:
        return entry | {"time_limit_ms": limit.ms, "time_limit_basis": limit.basis or None}
    entry |= _details(verdict)
    if case.note:
        entry["note"] = case.note
    outcome = verdict.outcome
    if isinstance(outcome, Returned | Raised | InvalidOutput) and outcome.stdout:
        entry["stdout"] = outcome.stdout
    return entry


def _details(verdict: CaseVerdict) -> dict[str, JsonValue]:
    run_input = verdict.case.input
    match verdict.outcome:
        case Returned(output=output):
            expected = verdict.case.expected
            mismatch = verdict.mismatch
            return {
                "input": _input(run_input),
                "expected": expected.value if expected else None,
                "actual": output,
                "reason": mismatch.detail if mismatch and mismatch.detail else None,
            }
        case Raised(error=error, op_index=op_index, partial_output=partial):
            return {
                "input": _input(operations_up_to(run_input, op_index)),
                "error": _error(error),
                "op_index": op_index,
                "partial_output": list(partial),
            }
        case InvalidOutput(reason=reason):
            return {"input": _input(run_input), "reason": reason}
        case TimedOut(limit_ms=limit_ms):
            return {"input": _input(run_input), "hang_guard_ms": limit_ms}
        case Crashed(exit_code=exit_code, stderr_tail=stderr_tail):
            return {"input": _input(run_input), "exit_code": exit_code, "stderr": list(stderr_tail)}
        case NotRun(reason=reason):
            return {"reason": reason}
        case StressCompleted() | Stalled() as outcome:
            return {"reason": outcome_summary(outcome)}


def _oracle(oracle: OracleStress | None, verdicts: Sequence[CaseVerdict]) -> JsonValue:
    """`cstudy test --stress N` on other problems: the approach and every judged input in seed
    order (none when the code did not build or load, like `cases`)."""
    if oracle is None:
        return None
    by_id = {verdict.case.id: verdict for verdict in verdicts}
    inputs: list[JsonValue] = []
    for found in oracle.inputs:
        if found.case_id in by_id:
            entry: dict[str, JsonValue] = {"seed": found.seed, "n": found.n}
            inputs.append(entry | _case(by_id[found.case_id]))
    return {"approach": oracle.approach, "inputs": inputs}


def _input(run_input: RunInput) -> JsonValue:
    """The tests.json encoding: arguments by name, or `ops` and `args`."""
    if isinstance(run_input, FunctionInput):
        return dict(run_input.arguments)
    return {"ops": list(run_input.ops), "args": [list(arguments) for arguments in run_input.args]}


def _error(error: UserError) -> JsonValue:
    return {"type": error.type, "message": error.message, "trace": error.trace}


def _stress(verdict: StressVerdict) -> JsonValue:
    """The shape docs/specs/cli.md#concurrent-problems specifies, with every failing run."""
    median = verdict.median_ms
    return {
        "id": verdict.case_id,
        "variant": verdict.variant.value,
        "status": status_value(verdict.status),
        "runs": len(verdict.runs),
        "runs_passed": verdict.runs_passed,
        "median_ms": round(median, DECIMALS) if median is not None else None,
        "failures": [_failed_run(run) for run in verdict.runs if not run.passed],
    }


def _failed_run(run: StressRunResult) -> JsonValue:
    return {
        "run": run.run,
        "seed": run.seed,
        "status": status_value(run.status),
        "reasons": list(run.reasons),
    }
