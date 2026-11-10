"""`cstudy dev` (docs/specs/service-projects.md#how-you-reach-them): the dev stack, in the
foreground. It prints where your app answers and the mock servers it can call, then what your app
prints, until Ctrl-C brings the stack down and keeps its data. `--events` writes the same as JSON
events for the Web UI (`dev_events.py`).

`--no-run` keeps the app idle, `--debug` runs it under its debugger, `--reset-data` starts from
empty data, and `--exec -- <command>` runs one command in the app's environment instead, with
`--network` where the install runs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.text import Text
from typer._click import Context as ClickContext
from typer.core import TyperCommand

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.environment import Environment
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.application.service_dev import (
    DevCommand,
    DevRequest,
    DevStack,
    run_dev_command,
    run_dev_stack,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.sandbox import CommandOutcome, StackStartError
from coding_study.entrypoints.commands.dev_events import stream_dev, terminated_as_interrupt
from coding_study.entrypoints.shared import (
    END_OF_OPTIONS,
    OPTIONAL_TARGET_HELP,
    ExitCode,
    add_command,
    command_environ,
    console,
)

NAME = "dev"
LABEL_WIDTH = 11
SCENARIO_SEPARATOR = "="
COMMAND_KEY = "cstudy.dev.command"
"""Where the words after `--` wait in the command's context."""
SCENARIO_HELP = "A mock server's visible scenario to start with; repeat it for several."
EVENTS_HELP = "The stack as JSON events, one per line; each line of input switches a scenario."
NO_RUN_HELP = "Keep the app container idle instead of running your app, for an IDE or a debugger."
DEBUG_HELP = "Run your app under its debugger and publish its port on 127.0.0.1."
RESET_DATA_HELP = "Remove the dev stack's data before it starts."
EXEC_HELP = "Run the command after -- in a one-off app container of the stack, then exit."
NETWORK_HELP = "With --exec: give the command the internet and no stack, to add a dependency."
STOPPED = "the stack is down and its data is kept"


class _CommandAfterDoubleDash(TyperCommand):
    """The words after `--` are `--exec`'s command, never the slug."""

    def parse_args(self, ctx: ClickContext, args: list[str]) -> list[str]:
        if END_OF_OPTIONS in args:
            end = args.index(END_OF_OPTIONS)
            ctx.meta[COMMAND_KEY] = tuple(args[end + 1 :])
            args = args[:end]
        return super().parse_args(ctx, args)


def register(app: typer.Typer) -> None:
    add_command(app, dev, NAME, _CommandAfterDoubleDash)


@dataclass(frozen=True, slots=True)
class _Flags:
    scenarios: bool = False
    events: bool = False
    no_run: bool = False
    debug: bool = False
    reset_data: bool = False
    exec: bool = False
    network: bool = False
    command: tuple[str, ...] | None = None
    """The words after `--`; None without `--`."""

    @property
    def refusal(self) -> str | None:
        """Why these flags do not go together; None when they do."""
        if self.network and not self.exec:
            return "--network goes with --exec"
        if self.exec:
            return self._exec_refusal
        if self.command is not None:
            return "a command after -- needs --exec: cstudy dev --exec -- <command>"
        if self.events and (self.no_run or self.debug or self.reset_data):
            return "--events takes --scenario alone"
        return None

    @property
    def _exec_refusal(self) -> str | None:
        if not self.command:
            return "--exec takes a command after --: cstudy dev --exec -- <command>"
        if self.no_run or self.debug or self.events:
            return "--exec takes no --no-run, --debug or --events"
        if self.network and (self.scenarios or self.reset_data):
            return "--exec --network runs no stack, so it takes no --scenario or --reset-data"
        return None


def dev(
    context: typer.Context,
    slug: Annotated[str | None, typer.Argument(help=OPTIONAL_TARGET_HELP)] = None,
    scenario: Annotated[
        list[str] | None,
        typer.Option("--scenario", metavar="MOCK=SCENARIO", help=SCENARIO_HELP),
    ] = None,
    events: Annotated[bool, typer.Option("--events", help=EVENTS_HELP)] = False,
    no_run: Annotated[bool, typer.Option("--no-run", help=NO_RUN_HELP)] = False,
    debug: Annotated[bool, typer.Option("--debug", help=DEBUG_HELP)] = False,
    reset_data: Annotated[bool, typer.Option("--reset-data", help=RESET_DATA_HELP)] = False,
    exec_command: Annotated[bool, typer.Option("--exec", help=EXEC_HELP)] = False,
    network: Annotated[bool, typer.Option("--network", help=NETWORK_HELP)] = False,
) -> None:
    """Run a service project's stack in the foreground, until Ctrl-C."""
    command: tuple[str, ...] | None = context.meta.get(COMMAND_KEY)
    flags = _Flags(
        bool(scenario), events, no_run, debug, reset_data, exec_command, network, command
    )
    refusal = flags.refusal
    if refusal is not None:
        raise UsageError(refusal)
    scenarios = dict(_scenario(text) for text in scenario or ())
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    request = DevRequest(target.slug, target.language, scenarios, no_run, debug, reset_data)
    if events:
        raise typer.Exit(stream_dev(environment, request))
    output = console(context)
    if command is not None:
        _exec(environment, request, DevCommand(command, network, _printed(output)), output)
    _foreground(environment, request, output)


def _foreground(environment: Environment, request: DevRequest, output: Console) -> NoReturn:
    try:
        with terminated_as_interrupt():
            ended = run_dev_stack(environment, request, _Printer(output), _notice(output))
    except KeyboardInterrupt:
        output.print(_line("stopped", STOPPED))
        raise typer.Exit(ExitCode.SUCCESS) from None
    except StackStartError as failure:
        _your_code_failed(failure, output)
    output.print(_line("stopped", f"your app exited with code {ended.exit_code}"))
    raise typer.Exit(ExitCode.USER_CODE_ERROR)


def _exec(
    environment: Environment, request: DevRequest, command: DevCommand, output: Console
) -> NoReturn:
    """Exit 0 when the command exits 0, and 2 with its exit code otherwise, as your code."""
    try:
        with terminated_as_interrupt():
            ended = run_dev_command(environment, request, command, _notice(output))
    except KeyboardInterrupt:
        output.print(_line("stopped", "your command was interrupted"))
        raise typer.Exit(ExitCode.INTERRUPTED) from None
    except StackStartError as failure:
        _your_code_failed(failure, output)
    if ended.exit_code == 0 and not ended.timed_out:
        raise typer.Exit(ExitCode.SUCCESS)
    output.print(_line("stopped", _command_end(ended)))
    raise typer.Exit(ExitCode.USER_CODE_ERROR)


def _command_end(ended: CommandOutcome) -> str:
    if ended.timed_out:
        return "your command did not finish within its limit and was stopped"
    return f"your command exited with code {ended.exit_code}"


def _your_code_failed(failure: StackStartError, output: Console) -> NoReturn:
    """Exit 2 with what your code printed; any other start failure raises on, to exit 4."""
    if not failure.failure.is_your_code:
        raise failure
    output.print(Text(str(failure), style="bold red"))
    for line in failure.output.splitlines():
        output.print(Text(line, style="dim"))
    raise typer.Exit(ExitCode.USER_CODE_ERROR) from None


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
        app = stack.app_url if stack.app_running else f"{stack.app_url} · idle, with --no-run"
        output.print(_line("app", app))
        if stack.debug_address is not None:
            output.print(_line("debug", stack.debug_address))
        for mock in stack.mocks:
            scenario = stack.scenarios.get(mock)
            output.print(_line("mock", mock if scenario is None else f"{mock} · {scenario}"))
        output.print(_line("stop", "Ctrl-C"))

    def app_line(self, line: str) -> None:
        self._output.print(Text(line))


def _printed(output: Console):
    def printed(line: str) -> None:
        output.print(Text(line))

    return printed


def _notice(output: Console):
    def noticed(line: str) -> None:
        output.print(Text(line, style="dim"))

    return noticed


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
