"""`cstudy hint` (docs/specs/cli.md#cstudy-hint)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.application.reveal_hint import HintsLocked, reveal_hint
from coding_study.entrypoints.shared import (
    OPTIONAL_TARGET_HELP,
    add_command,
    command_environ,
    console,
)

NAME = "hint"
NO_MORE_HINTS = "no more hints"


def register(app: typer.Typer) -> None:
    add_command(app, hint, NAME)


def hint(
    context: typer.Context,
    slug: Annotated[
        str | None,
        typer.Argument(help=OPTIONAL_TARGET_HELP),
    ] = None,
) -> None:
    """Reveal the next hint."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    revealed = reveal_hint(environment, target.slug)
    output = console(context)
    if revealed is None:
        output.print(NO_MORE_HINTS)
        return
    if isinstance(revealed, HintsLocked):
        output.print(f"{NO_MORE_HINTS} until level {revealed.level} opens")
        return
    output.print(Text(f"{revealed.slug} · hint {revealed.number} of {revealed.total}", "bold"))
    output.print(Text(revealed.text))
