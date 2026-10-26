"""The `cstudy` command line (docs/specs/cli.md): global options and command registration.

Each command lives in its own module under `entrypoints/commands/`; this module never changes
when a command does.
"""

from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from coding_study.entrypoints.commands import COMMAND_REGISTRATIONS
from coding_study.entrypoints.shared import CsGroup, GlobalOptions

app = typer.Typer(
    cls=CsGroup,
    name="cstudy",
    help="Local, IDE-first interview practice.",
    no_args_is_help=True,
    add_completion=False,
)


def print_version_and_exit(requested: bool) -> None:
    """The version comes from the installed package metadata, which `pyproject.toml` owns."""
    if requested:
        typer.echo(f"cstudy {version('coding-study')}")
        raise typer.Exit


@app.callback()
def global_options(
    context: typer.Context,
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print the version and exit.",
            callback=print_version_and_exit,
            is_eager=True,
        ),
    ] = False,
    no_color: Annotated[
        bool, typer.Option("--no-color", help="Plain output (also with NO_COLOR or no TTY).")
    ] = False,
    workspace: Annotated[
        Path | None,
        typer.Option(
            "--workspace",
            help="The workspace (default: CSTUDY_WORKSPACE, the nearest one above, or here).",
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content",
            help="Read problems, tracks and runners from this checkout (default: CSTUDY_CONTENT).",
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    context.obj = GlobalOptions(no_color=no_color, workspace=workspace, content=content)


for register in COMMAND_REGISTRATIONS:
    register(app)


def main() -> None:
    app()
