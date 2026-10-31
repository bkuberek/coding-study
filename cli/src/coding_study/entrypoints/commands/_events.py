"""`--events`: a run as JSON events, one per line on standard output
(docs/specs/cli.md#event-stream).

Each event is written and flushed as soon as the run reports it. The command ends the stream with
`run_end`, which carries the document `--json` prints, or the error that stopped the run once it
had started; a run that stops before it starts writes no event at all. SIGINT and SIGTERM end it
as interrupted.
"""

import json
import signal
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from types import FrameType

import typer

from coding_study.application.run_events import (
    BuildEnded,
    CaseGraded,
    CaseRevised,
    CaseStarted,
    DiagnosticFound,
    EventSink,
    LevelGraded,
    LevelOpened,
    OutputLine,
    PerfChecked,
    PlannedCases,
    RunEvent,
    RunStarted,
    StressGraded,
    StressRunJudged,
    StressRunStarted,
    SuiteTestReported,
    SuiteTestStarted,
)
from coding_study.application.submit_project import OpenedLevel
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.generated_cases import OracleInput
from coding_study.domain.stress_runs import PlannedRun
from coding_study.entrypoints.commands._diagnostics import diagnostic_value
from coding_study.entrypoints.commands.bench import perf_value
from coding_study.entrypoints.commands.project_documents import level_tally_value, suite_test_value
from coding_study.entrypoints.commands.run_document import (
    DECIMALS,
    case_value,
    stress_run_value,
    stress_value,
    timer_value,
)
from coding_study.entrypoints.shared import ERROR_EXIT_CODES, ExitCode

EVENTS_VERSION = 1
ERROR_OUTCOME = "error"
INTERRUPTED_OUTCOME = "interrupted"
LEVEL_PASSED = "pass"
LEVEL_FAILED = "fail"
TERMINATED_EXIT_CODE = 128 + signal.SIGTERM
"""SIGTERM ends a run as SIGINT does, with the shell's exit code for it."""


@dataclass(frozen=True, slots=True)
class RunSummary:
    exit_code: int
    document: dict[str, JsonValue]
    """What `--json` prints; its `outcome` is the stream's."""


def require_events_alone(given: Sequence[str]) -> None:
    """`--events` is the whole of standard output: no document, rerun or debug session beside
    it."""
    if given:
        raise UsageError(f"--events excludes {', '.join(given)}")


def write_events[R](run: Callable[[EventSink], R], summarize: Callable[[R], RunSummary]) -> int:
    """Runs with every event written as it comes, ends the stream and returns the exit code.

    An error after the start ends the stream, then propagates, so that `error: ...` still reaches
    standard error; Ctrl-C ends it and exits 130, SIGTERM 143. Either unwinds the run, which kills
    the runner's process group.
    """
    stream = _Stream()
    try:
        with _terminated_like_interrupt():
            result = run(stream.emit)
    except tuple(ERROR_EXIT_CODES) as error:
        stream.stop(ERROR_OUTCOME, ERROR_EXIT_CODES[type(error)], str(error))
        raise
    except KeyboardInterrupt:
        stream.stop(INTERRUPTED_OUTCOME, ExitCode.INTERRUPTED, None)
        raise typer.Exit(ExitCode.INTERRUPTED) from None
    except _Terminated:
        stream.stop(INTERRUPTED_OUTCOME, TERMINATED_EXIT_CODE, None)
        raise typer.Exit(TERMINATED_EXIT_CODE) from None
    summary = summarize(result)
    stream.finish(summary)
    return summary.exit_code


class _Stream:
    """Ends with `run_end` only once `run_start`, the first event of every run, is written."""

    def __init__(self) -> None:
        self._started = False

    def emit(self, event: RunEvent) -> None:
        self._started = True
        _write(event_value(event))

    def finish(self, summary: RunSummary) -> None:
        document = summary.document
        ending: dict[str, JsonValue] = {
            "outcome": document["outcome"],
            "exit_code": summary.exit_code,
            "message": None,
            "summary": document,
        }
        _write(_event("run_end", ending))

    def stop(self, outcome: str, exit_code: int, message: str | None) -> None:
        """Ends a run that stopped without a result."""
        if not self._started:
            return
        ending: dict[str, JsonValue] = {
            "outcome": outcome,
            "exit_code": exit_code,
            "message": message,
            "summary": None,
        }
        _write(_event("run_end", ending))


class _Terminated(BaseException):
    """SIGTERM, raised where the run is, like KeyboardInterrupt for SIGINT."""


@contextmanager
def _terminated_like_interrupt() -> Generator[None]:
    """Off the main thread, where no handler can be set, SIGTERM keeps its default."""

    def stop(_signal_number: int, _frame: FrameType | None) -> None:
        raise _Terminated

    try:
        previous = signal.signal(signal.SIGTERM, stop)
    except ValueError:
        yield
        return
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def event_value(event: RunEvent) -> dict[str, JsonValue]:
    match event:
        case RunStarted():
            return _event("run_start", _start_fields(event))
        case OutputLine(text=text):
            return _event("output", {"text": text})
        case BuildEnded(seconds=seconds, note=note):
            return _event("build", {"seconds": round(seconds, DECIMALS), "note": note})
        case SuiteTestStarted(test_id=test_id):
            return _event("test_start", {"id": test_id})
        case SuiteTestReported(verdict=verdict):
            return _event("test_result", suite_test_value(verdict))
        case CaseStarted(case=case, level=level, oracle=oracle):
            started = {"id": case.id, "visible": case.visible, "level": level}
            return _event("case_start", started | _oracle_fields(oracle))
        case CaseGraded(verdict=verdict, level=level, oracle=oracle):
            graded = case_value(verdict) | {"level": level}
            return _event("case_result", graded | _oracle_fields(oracle))
        case CaseRevised(verdict=verdict, level=level):
            return _event("case_revised", case_value(verdict) | {"level": level})
        case StressRunStarted(planned=planned):
            return _event("stress_run_start", _stress_run_fields(planned))
        case StressRunJudged(planned=planned, result=result):
            judged = stress_run_value(result) | {"duration_ns": result.duration_ns}
            return _event("stress_run", _stress_run_fields(planned) | judged)
        case StressGraded(verdict=verdict):
            return _event("stress_result", stress_value(verdict))
        case DiagnosticFound(diagnostic=diagnostic):
            return _event("diagnostic", diagnostic_value(diagnostic))
        case LevelGraded(tally=tally):
            counts = level_tally_value(tally)
            assert isinstance(counts, dict)
            status = LEVEL_PASSED if tally.all_passed else LEVEL_FAILED
            return _event("level_result", {"status": status} | counts)
        case LevelOpened(opened=opened):
            return _event("level_unlocked", _opened_fields(opened))
        case PerfChecked(bench=bench):
            return _event("perf_result", perf_value(bench))


def _event(event_type: str, fields: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {"type": event_type, "version": EVENTS_VERSION, **fields}


def _start_fields(started: RunStarted) -> dict[str, JsonValue]:
    levels = started.levels
    meta, attempt = started.meta, started.attempt
    return {
        "command": started.command.value,
        "slug": meta.slug,
        "language": started.language.value,
        "attempt_id": attempt.id,
        "mode": attempt.mode.value,
        "levels": None
        if levels is None
        else {
            "up_to": levels.ran_up_to,
            "unlocked": levels.unlocked,
            "last": levels.progress.last,
        },
        "kind": meta.kind.value,
        "track": meta.track.value,
        "timer": timer_value(attempt, started.at),
        "time_limit": str(started.time_limit) if started.time_limit else None,
        "planned": _planned_fields(started.planned),
    }


def _planned_fields(planned: PlannedCases | None) -> JsonValue:
    if planned is None:
        return None
    stress = planned.stress
    return {
        "cases": planned.cases,
        "visible": planned.visible,
        "hidden": planned.hidden,
        "generated": planned.generated,
        "oracle_inputs": planned.oracle_inputs,
        "stress": None
        if stress is None
        else {"cases": stress.cases, "variants": stress.variants, "runs": stress.runs},
    }


def _oracle_fields(oracle: OracleInput | None) -> dict[str, JsonValue]:
    """An oracle input of `cstudy test --stress N` says so, with its seed and size."""
    if oracle is None:
        return {}
    return {"oracle": True, "seed": oracle.seed, "n": oracle.n}


def _stress_run_fields(planned: PlannedRun) -> dict[str, JsonValue]:
    return {
        "id": planned.case.id,
        "variant": planned.variant.value,
        "run": planned.run,
        "seed": planned.seed,
    }


def _opened_fields(opened: OpenedLevel) -> dict[str, JsonValue]:
    tests = opened.tests
    return {
        "level": opened.level,
        "title": opened.title,
        "methods": list(opened.methods),
        "tests": None if tests is None else {"path": tests.path, "count": tests.tests},
        "statement": opened.statement,
    }


def _write(event: dict[str, JsonValue]) -> None:
    """One line, flushed at once (`typer.echo` flushes), so a reader sees it as it happens."""
    typer.echo(json.dumps(event))
