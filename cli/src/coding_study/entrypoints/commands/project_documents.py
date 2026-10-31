"""JSON documents of the project commands (docs/specs/cli.md#project-problems): `cstudy test`
on a project problem, in the style of `cstudy test --json`."""

from coding_study.application.project_testing import ProjectTestResult
from coding_study.domain.cases import JsonValue
from coding_study.domain.project_test_runs import SuiteTestVerdict
from coding_study.domain.runs import Crashed, Raised, TimedOut, UserError
from coding_study.domain.suite_runs import AssertionFailed, Passed, Skipped
from coding_study.entrypoints.commands.run_document import (
    DECIMALS,
    error_value,
    levels_value,
    tally_value,
    timer_value,
)

NO_BUILD: JsonValue = {"seconds": 0.0, "note": None, "diagnostics": []}
"""A project folder builds nothing before its suite runs."""
CRASH_TYPE = "crash"
"""The `error.type` of a test during which the runner process ended."""


def project_test_document(result: ProjectTestResult, exit_code: int) -> dict[str, JsonValue]:
    """`comparator` and `oracle` are null and `stress` empty: a suite is the framework's verdict,
    and no level opens from it."""
    load_error = result.report.load_error
    return {
        "slug": result.meta.slug,
        "language": result.language.value,
        "attempt_id": result.attempt.id,
        "outcome": _test_outcome(result),
        "exit_code": exit_code,
        "every_case": result.every_case,
        "comparator": None,
        "time_limit": None,
        "timer": timer_value(result.attempt, result.ran_at),
        "levels": levels_value(result.levels),
        "build": NO_BUILD,
        "load_error": error_value(load_error) if load_error else None,
        "cases": [suite_test_value(verdict) for verdict in result.verdicts],
        "oracle": None,
        "stress": [],
        "tally": tally_value(result.tally),
        "duration_s": round(result.duration_seconds, DECIMALS),
    }


def suite_test_value(verdict: SuiteTestVerdict) -> dict[str, JsonValue]:
    """`id`, `status`, `duration_ns`, `origin` and `level`, then what the report shows."""
    outcome = verdict.test.outcome
    entry: dict[str, JsonValue] = {
        "id": verdict.test.test_id,
        "status": verdict.status.name.lower(),
        "duration_ns": _duration_ns(verdict),
        "origin": verdict.origin.value,
        "level": verdict.level,
    }
    match outcome:
        case AssertionFailed(message=message, comparison=comparison):
            entry["message"] = message
            if comparison is not None:
                entry |= {"expected": comparison.expected, "actual": comparison.actual}
        case Raised(error=error):
            entry["error"] = error_value(error)
        case Skipped(message=message):
            entry["message"] = message
        case TimedOut(limit_ms=limit_ms):
            entry["message"] = f"timed out after {limit_ms} ms (hang guard)"
        case Crashed(exit_code=code, stderr_tail=stderr_tail):
            crash = UserError(CRASH_TYPE, f"runner exited with code {code}", "\n".join(stderr_tail))
            entry["error"] = error_value(crash)
        case Passed():
            pass
    stdout = _stdout(verdict)
    if stdout:
        entry["stdout"] = stdout
    return entry


def _test_outcome(result: ProjectTestResult) -> str:
    if result.report.load_error is not None:
        return "load_failed"
    return "passed" if result.passed else "failed"


def _duration_ns(verdict: SuiteTestVerdict) -> int | None:
    outcome = verdict.test.outcome
    if isinstance(outcome, Passed | AssertionFailed | Raised | Skipped):
        return outcome.duration_ns
    return None


def _stdout(verdict: SuiteTestVerdict) -> str:
    outcome = verdict.test.outcome
    if isinstance(outcome, Passed | AssertionFailed | Raised | Skipped):
        return outcome.stdout
    return ""
