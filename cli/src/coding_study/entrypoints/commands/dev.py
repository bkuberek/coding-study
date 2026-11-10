"""`cstudy dev` (docs/specs/service-projects.md#how-you-reach-them): the dev stack, in the
foreground. It prints where your app answers and the mock servers it can call, then what your app
prints, until Ctrl-C brings the stack down and keeps its data. `--events` writes the same as JSON
events for the Web UI (`dev_events.py`).
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.application.service_dev import DevRequest, DevStack, run_dev_stack
from coding_study.domain.errors import UsageError
from coding_study.domain.sandbox import StackStartError
from coding_study.entrypoints.commands.dev_events import stream_dev, terminated_as_interrupt
from coding_study.entrypoints.shared import (
    OPTIONAL_TARGET_HELP,
    ExitCode,
    add_command,
    command_environ,
    console,
)

NAME = "dev"
LABEL_WIDTH = 11
SCENARIO_SEPARATOR = "="
SCENARIO_HELP = "A mock server's visible scenario to start with; repeat it for several."
EVENTS_HELP = "The stack as JSON events, one per line; each line of input switches a scenario."


def register(app: typer.Typer) -> None:
    add_command(app, dev, NAME)


def dev(
    context: typer.Context,
    slug: Annotated[str | None, typer.Argument(help=OPTIONAL_TARGET_HELP)] = None,
    scenario: Annotated[
        list[str] | None,
        typer.Option("--scenario", metavar="MOCK=SCENARIO", help=SCENARIO_HELP),
    ] = None,
    events: Annotated[
        bool,
        typer.Option("--events", help=EVENTS_HELP),
    ] = False,
) -> None:
    """Run a service project's stack in the foreground, until Ctrl-C."""
    scenarios = dict(_scenario(text) for text in scenario or ())
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    request = DevRequest(target.slug, target.language, scenarios)
    if events:
        raise typer.Exit(stream_dev(environment, request))
    output = console(context)
    try:
        with terminated_as_interrupt():
            ended = run_dev_stack(environment, request, _Printer(output), _notice(output))
    except KeyboardInterrupt:
        output.print(_line("stopped", "the stack is down and its data is kept"))
        raise typer.Exit(ExitCode.SUCCESS) from None
    except StackStartError as failure:
        if not failure.failure.is_your_code:
            raise
        output.print(Text(str(failure), style="bold red"))
        for line in failure.output.splitlines():
            output.print(Text(line, style="dim"))
        raise typer.Exit(ExitCode.USER_CODE_ERROR) from None
    output.print(_line("stopped", f"your app exited with code {ended.exit_code}"))
    raise typer.Exit(ExitCode.USER_CODE_ERROR)


def _scenario(text: str) -> tuple[str, str]:
    mock, separator, scenario = text.partition(SCENARIO_SEPARATOR)
    if not (mock and separator and scenario):
        raise UsageError(f"--scenario takes MOCK=SCENARIO, not {text}")
    return mock, scenario


class _Printer:
    def __init__(self, output: Console) -> None:
        self._output = output

    def stack_ready(self, stack: DevStack) -> None:
        output = self._output
        output.print(_line("app", stack.app_url))
        for mock in stack.mocks:
            scenario = stack.scenarios.get(mock)
            output.print(_line("mock", mock if scenario is None else f"{mock} · {scenario}"))
        output.print(_line("stop", "Ctrl-C"))

    def app_line(self, line: str) -> None:
        self._output.print(Text(line))


def _notice(output: Console):
    def noticed(line: str) -> None:
        output.print(Text(line, style="dim"))

    return noticed


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
