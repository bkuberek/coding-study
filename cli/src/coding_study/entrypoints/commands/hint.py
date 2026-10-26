"""`cstudy hint` (docs/specs/cli.md#cstudy-hint)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.reveal_hint import reveal_hint
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "hint"
NO_MORE_HINTS = "no more hints"


def register(app: typer.Typer) -> None:
    add_command(app, hint, NAME)


def hint(
    context: typer.Context,
    slug: Annotated[
        str | None, typer.Argument(help="The problem; default: the active attempt.")
    ] = None,
) -> None:
    """Reveal the next hint."""
    revealed = reveal_hint(
        load_environment(Path.cwd(), command_environ(context), Path.home()), slug
    )
    output = console(context)
    if revealed is None:
        output.print(NO_MORE_HINTS)
        return
    output.print(Text(f"{revealed.slug} · hint {revealed.number} of {revealed.total}", "bold"))
    output.print(Text(revealed.text))
