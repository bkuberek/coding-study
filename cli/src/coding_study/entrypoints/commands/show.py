"""`cstudy show` (docs/specs/cli.md#cstudy-show)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_catalog_environment
from coding_study.application.resolve_target import ProblemTarget, resolve_problem
from coding_study.application.show_statement import ShowRequest, show_statement
from coding_study.entrypoints.shared import (
    PROBLEM_TARGET_HELP,
    add_command,
    command_environ,
    console,
)

NAME = "show"


def register(app: typer.Typer) -> None:
    add_command(app, show, NAME)


def show(
    context: typer.Context,
    slug: Annotated[str, typer.Argument(help=PROBLEM_TARGET_HELP)],
    level: Annotated[
        int | None,
        typer.Option(
            "--level", metavar="N", min=1, help="Progressive: show levels 1 to N (unlocked only)."
        ),
    ] = None,
) -> None:
    """Print the rendered statement (never hints)."""
    environment = load_catalog_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_problem(environment, ProblemTarget(slug), Path.cwd())
    statement = show_statement(environment, ShowRequest(target.slug, level))
    console(context).print(Text(statement), end="")
