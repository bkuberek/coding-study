"""What every command module uses: exit codes, consoles, and registration with error mapping."""

import functools
import os
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.text import Text
from typer._click import Context as ClickContext
from typer.core import TyperCommand, TyperGroup

from coding_study.adapters.locations import (
    CONTENT_VARIABLE,
    WORKSPACE_VARIABLE,
    ContentRootError,
    WorkspaceError,
)
from coding_study.domain.errors import (
    ConfigError,
    ContentError,
    LanguageNotSetUpError,
    RunnerProtocolError,
    RunnerStartError,
    UnknownProblemError,
    UsageError,
    VersionControlError,
)


class ExitCode(IntEnum):
    """docs/specs/cli.md#exit-codes"""

    SUCCESS = 0
    FAILURES = 1
    USER_CODE_ERROR = 2
    USAGE_ERROR = 3
    ENVIRONMENT_ERROR = 4
    CONTENT_ERROR = 5
    INTERNAL_ERROR = 70
    INTERRUPTED = 130


ERROR_EXIT_CODES: Mapping[type[Exception], ExitCode] = {
    UnknownProblemError: ExitCode.USAGE_ERROR,
    ContentError: ExitCode.CONTENT_ERROR,
    ConfigError: ExitCode.ENVIRONMENT_ERROR,
    LanguageNotSetUpError: ExitCode.ENVIRONMENT_ERROR,
    RunnerStartError: ExitCode.ENVIRONMENT_ERROR,
    RunnerProtocolError: ExitCode.INTERNAL_ERROR,
    UsageError: ExitCode.USAGE_ERROR,
    ContentRootError: ExitCode.USAGE_ERROR,
    WorkspaceError: ExitCode.USAGE_ERROR,
    VersionControlError: ExitCode.ENVIRONMENT_ERROR,
}
ERROR_PREFIX = "error: "
CLICK_USAGE_EXIT_CODE = 2
"""What Click exits with for bad flags, unknown commands and invalid values."""


@dataclass(frozen=True, slots=True)
class GlobalOptions:
    no_color: bool = False
    workspace: Path | None = None
    content: Path | None = None

    def environ(self, base: Mapping[str, str]) -> dict[str, str]:
        """`base` with `--workspace` and `--content` as CSTUDY_WORKSPACE and CSTUDY_CONTENT, which
        they override (docs/specs/installation-and-workspaces.md)."""
        overrides = {WORKSPACE_VARIABLE: self.workspace, CONTENT_VARIABLE: self.content}
        return {**base, **{name: str(path) for name, path in overrides.items() if path}}


def command_environ(context: typer.Context) -> dict[str, str]:
    """The process environment with the global flags applied, for `load_environment`."""
    return context.ensure_object(GlobalOptions).environ(os.environ)


def console(context: typer.Context) -> Console:
    options: GlobalOptions = context.ensure_object(GlobalOptions)
    return Console(no_color=options.no_color, highlight=False, soft_wrap=True)


END_OF_OPTIONS = "--"


def optional_value_command(option: str) -> type[TyperCommand]:
    """A command whose `option` takes a value only as `option=VALUE`: a bare `option` becomes
    `option=`, so the next token stays an argument (`cstudy test --time-limit two-sum`)."""

    class _OptionalValueCommand(TyperCommand):
        def parse_args(self, ctx: ClickContext, args: list[str]) -> list[str]:
            end = args.index(END_OF_OPTIONS) if END_OF_OPTIONS in args else len(args)
            options = [f"{option}=" if arg == option else arg for arg in args[:end]]
            return super().parse_args(ctx, [*options, *args[end:]])

    return _OptionalValueCommand


def add_command[**P](
    app: typer.Typer,
    callback: Callable[P, None],
    name: str,
    command_class: type[TyperCommand] | None = None,
) -> None:
    """Register `callback` as `cstudy <name>`; known errors become messages and spec exit codes."""
    app.command(name, cls=command_class)(_exit_codes_for_known_errors(callback))


def print_error(error: Exception) -> None:
    """`error: <message>` on standard error, as plain text (never read as markup)."""
    Console(stderr=True, highlight=False, soft_wrap=True).print(Text(f"{ERROR_PREFIX}{error}"))


class CsGroup(TyperGroup):
    """The `cstudy` command group: usage errors exit 3 (docs/specs/cli.md#exit-codes), not 2."""

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: ClickContext | None = None,
        **extra: Any,
    ) -> ClickContext:
        with _usage_errors_exit_3():
            return super().make_context(info_name, args, parent, **extra)

    def invoke(self, ctx: ClickContext) -> Any:
        with _usage_errors_exit_3():
            return super().invoke(ctx)


@contextmanager
def _usage_errors_exit_3() -> Generator[None]:
    try:
        yield
    except typer.TyperException as error:
        if error.exit_code == CLICK_USAGE_EXIT_CODE:
            error.exit_code = ExitCode.USAGE_ERROR
        raise


def _exit_codes_for_known_errors[**P](callback: Callable[P, None]) -> Callable[P, None]:
    @functools.wraps(callback)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            callback(*args, **kwargs)
        except tuple(ERROR_EXIT_CODES) as error:
            print_error(error)
            raise typer.Exit(ERROR_EXIT_CODES[type(error)]) from error

    return wrapper
