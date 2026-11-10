"""`cstudy dev --events` (docs/specs/service-projects.md#the-dev-stack-from-the-page): the dev
stack as JSON events on standard output, one per line, for the Web UI, which keeps a pipe on
standard input to switch scenarios while the stack runs.

The progress notices come as `output` events, with the stack's stage, then `dev_ready` names where
the app answers and each mock server with its visible scenarios, and each line the app prints is an
`app` event. Each line of standard input, `{"mock": "room-vendor", "scenario": "outage"}` (`null`
for none), switches a scenario and is answered by a `scenario` event. `dev_end` is always the last
line, whatever ended the stack: Ctrl-C or SIGTERM, the app, or a refusal.
"""

import json
import signal
import sys
import threading
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from types import FrameType
from typing import Any, cast

import typer

from coding_study.application.environment import Environment
from coding_study.application.run_events import notice_event
from coding_study.application.service_dev import DevRequest, DevScenarios, DevStack, run_dev_stack
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import RunnerStartError, UsageError
from coding_study.domain.sandbox import StackStartError
from coding_study.entrypoints.commands._events import EVENTS_VERSION, event_value
from coding_study.entrypoints.commands.run_document import DECIMALS
from coding_study.entrypoints.shared import ERROR_EXIT_CODES, ExitCode

STOPPED = "the stack is down and its data is kept"
NOT_A_SWITCH = 'not a scenario switch: send {"mock": "<name>", "scenario": "<name>" or null}'


@contextmanager
def terminated_as_interrupt() -> Generator[None]:
    """SIGTERM brings the stack down as Ctrl-C does."""

    def interrupted(_signal_number: int, _frame: FrameType | None) -> None:
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def stream_dev(environment: Environment, request: DevRequest) -> int:
    """Runs the dev stack with every event written as it comes; returns the exit code `cstudy dev`
    ends with, and raises an error that is not your code after `dev_end`, so `error: ...` still
    reaches standard error."""
    stream = _DevStream()
    try:
        with terminated_as_interrupt():
            ended = run_dev_stack(environment, request, stream, stream.notice)
    except KeyboardInterrupt:
        stream.end("stopped", ExitCode.SUCCESS, STOPPED)
        return ExitCode.SUCCESS
    except StackStartError as failure:
        if not failure.failure.is_your_code:
            stream.end("error", ExitCode.ENVIRONMENT_ERROR, str(failure))
            raise
        stream.end("load_failed", ExitCode.USER_CODE_ERROR, str(failure), failure.output)
        return ExitCode.USER_CODE_ERROR
    except tuple(ERROR_EXIT_CODES) as error:
        stream.end("error", ERROR_EXIT_CODES[type(error)], str(error))
        raise
    exited = f"your app exited with code {ended.exit_code}"
    stream.end("app_exited", ExitCode.USER_CODE_ERROR, exited)
    return ExitCode.USER_CODE_ERROR


class _DevStream:
    """Writes each event whole, from the stack's thread and from the one reading standard input."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def notice(self, line: str) -> None:
        self._write(event_value(notice_event(line)))

    def stack_ready(self, stack: DevStack) -> None:
        mocks: list[JsonValue] = [
            {
                "name": name,
                "scenario": stack.scenarios.get(name),
                "scenarios": list(stack.visible.get(name, ())),
            }
            for name in stack.mocks
        ]
        startup = round(stack.startup_seconds, DECIMALS)
        self._event("dev_ready", {"app_url": stack.app_url, "startup_s": startup, "mocks": mocks})
        if stack.control is not None:
            reader = threading.Thread(target=self._switches, args=(stack.control,), daemon=True)
            reader.start()

    def app_line(self, line: str) -> None:
        self._event("app", {"text": line})

    def end(self, outcome: str, exit_code: int, message: str, output: str | None = None) -> None:
        fields: dict[str, JsonValue] = {"outcome": outcome, "exit_code": exit_code}
        fields["message"] = message
        if output is not None:
            fields["output"] = output
        self._event("dev_end", fields)

    def _switches(self, control: DevScenarios) -> None:
        """Each line of standard input, until it ends."""
        for line in sys.stdin:
            if line.strip():
                self._switch(control, line)

    def _switch(self, control: DevScenarios, line: str) -> None:
        asked = _switch_of(line)
        if asked is None:
            self._event("scenario", {"mock": None, "scenario": None, "message": NOT_A_SWITCH})
            return
        mock, scenario = asked
        message: str | None = None
        try:
            control.switch(mock, scenario)
        except (UsageError, RunnerStartError) as refusal:
            message = str(refusal)
        held = control.current.get(mock)
        self._event("scenario", {"mock": mock, "scenario": held, "message": message})

    def _event(self, event_type: str, fields: Mapping[str, JsonValue]) -> None:
        self._write({"type": event_type, "version": EVENTS_VERSION, **fields})

    def _write(self, event: Mapping[str, JsonValue]) -> None:
        with self._lock:
            typer.echo(json.dumps(event))


def _switch_of(line: str) -> tuple[str, str | None] | None:
    """`(mock, scenario)` of a line `{"mock": ..., "scenario": ...}`; None for any other line."""
    try:
        document: Any = json.loads(line)
    except ValueError:
        return None
    if not isinstance(document, dict):
        return None
    fields = cast(dict[str, object], document)
    mock, scenario = fields.get("mock"), fields.get("scenario")
    if not isinstance(mock, str) or not (scenario is None or isinstance(scenario, str)):
        return None
    return mock, scenario
