"""`cstudy import` (docs/specs/cli.md#cstudy-import)."""

from pathlib import Path
from typing import Annotated

import typer

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.progress_backup import EXPORT_FILE, import_progress
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.commands.export import labelled, row_counts_text
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "import"


def register(app: typer.Typer) -> None:
    add_command(app, import_command, NAME)


def import_command(
    context: typer.Context,
    path: Annotated[
        Path | None,
        typer.Argument(
            help=f"A cstudy export file; default: {EXPORT_FILE} at the repository root."
        ),
    ] = None,
) -> None:
    """Restore a progress export into an empty progress.db."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    source = path or environment.root / EXPORT_FILE
    try:
        text = source.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise UsageError(f"no export at {source}; write one with cstudy export") from None
    except OSError as error:
        raise UsageError(f"cannot read {source}: {error.strerror}") from None
    row_counts = import_progress(environment, text)
    output = console(context)
    output.print(labelled("imported", row_counts_text(row_counts)))
    output.print(labelled("into", environment.config.progress_db))
