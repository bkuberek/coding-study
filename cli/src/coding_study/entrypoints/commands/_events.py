"""`--events`: a project run as JSON events, one per line on standard output
(docs/specs/cli.md#event-stream).

Each event is written and flushed as soon as the run reports it. The command ends the stream with
`run_end`, which carries the document `--json` prints, or the error that stopped the run once it
had started; a run that stops before it starts writes no event at all.
"""

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import typer

from coding_study.application.project_events import (
    CaseGraded,
    CaseStarted,
    DiagnosticFound,
    EventSink,
    LevelGraded,
    LevelOpened,
    OutputLine,
    ProjectEvent,
    RunStarted,
    SuiteTestReported,
    SuiteTestStarted,
)
from coding_study.application.submit_project import OpenedLevel
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.commands._diagnostics import diagnostic_value
from coding_study.entrypoints.commands.project_documents import level_tally_value, suite_test_value
from coding_study.entrypoints.commands.run_document import case_value
from coding_study.entrypoints.shared import ERROR_EXIT_CODES, ExitCode

EVENTS_VERSION = 1
ERROR_OUTCOME = "error"
INTERRUPTED_OUTCOME = "interrupted"
LEVEL_PASSED = "pass"
LEVEL_FAILED = "fail"


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
    standard error; Ctrl-C ends it and exits 130.
    """
    stream = _Stream()
    try:
        result = run(stream.emit)
    except tuple(ERROR_EXIT_CODES) as error:
        stream.stop(ERROR_OUTCOME, ERROR_EXIT_CODES[type(error)], str(error))
        raise
    except KeyboardInterrupt:
        stream.stop(INTERRUPTED_OUTCOME, ExitCode.INTERRUPTED, None)
        raise typer.Exit(ExitCode.INTERRUPTED) from None
    summary = summarize(result)
    stream.finish(summary)
    return summary.exit_code


class _Stream:
    """Ends with `run_end` only once `run_start`, the first event of every run, is written."""

    def __init__(self) -> None:
        self._started = False

    def emit(self, event: ProjectEvent) -> None:
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


def event_value(event: ProjectEvent) -> dict[str, JsonValue]:
    match event:
        case RunStarted():
            return _event("run_start", _start_fields(event))
        case OutputLine(text=text):
            return _event("output", {"text": text})
        case SuiteTestStarted(test_id=test_id):
            return _event("test_start", {"id": test_id})
        case SuiteTestReported(verdict=verdict):
            return _event("test_result", suite_test_value(verdict))
        case CaseStarted(case=case, level=level):
            return _event("case_start", {"id": case.id, "visible": case.visible, "level": level})
        case CaseGraded(verdict=verdict, level=level):
            return _event("case_result", case_value(verdict) | {"level": level})
        case DiagnosticFound(diagnostic=diagnostic):
            return _event("diagnostic", diagnostic_value(diagnostic))
        case LevelGraded(tally=tally):
            counts = level_tally_value(tally)
            assert isinstance(counts, dict)
            status = LEVEL_PASSED if tally.all_passed else LEVEL_FAILED
            return _event("level_result", {"status": status} | counts)
        case LevelOpened(opened=opened):
            return _event("level_unlocked", _opened_fields(opened))


def _event(event_type: str, fields: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {"type": event_type, "version": EVENTS_VERSION, **fields}


def _start_fields(started: RunStarted) -> dict[str, JsonValue]:
    levels = started.levels
    return {
        "command": started.command.value,
        "slug": started.meta.slug,
        "language": started.language.value,
        "attempt_id": started.attempt.id,
        "mode": started.attempt.mode.value,
        "levels": {
            "up_to": levels.ran_up_to,
            "unlocked": levels.unlocked,
            "last": levels.progress.last,
        },
    }


def _opened_fields(opened: OpenedLevel) -> dict[str, JsonValue]:
    return {
        "level": opened.level,
        "title": opened.title,
        "methods": list(opened.methods),
        "tests": {"path": opened.tests.path, "count": opened.tests.tests},
        "statement": opened.statement,
    }


def _write(event: dict[str, JsonValue]) -> None:
    """One line, flushed at once (`typer.echo` flushes), so a reader sees it as it happens."""
    typer.echo(json.dumps(event))
