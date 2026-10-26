"""`cstudy export` (docs/specs/cli.md#cstudy-export)."""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.progress_backup import EXPORT_FILE, export_progress
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "export"
LABEL_WIDTH = 10


def register(app: typer.Typer) -> None:
    add_command(app, export, NAME)


def export(
    context: typer.Context,
    out: Annotated[
        Path | None,
        typer.Option(
            "--out", metavar="PATH", help=f"Default: {EXPORT_FILE} at the repository root."
        ),
    ] = None,
) -> None:
    """Back up progress as JSON."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    backup = export_progress(environment)
    path = out or environment.root / EXPORT_FILE
    try:
        path.write_text(backup.text, encoding="utf-8")
    except OSError as error:
        raise UsageError(f"cannot write {path}: {error.strerror}") from None
    output = console(context)
    output.print(labelled("exported", row_counts_text(backup.row_counts)))
    output.print(labelled("file", str(out) if out else EXPORT_FILE))


def row_counts_text(row_counts: Mapping[str, int]) -> str:
    """`attempts 6 · test_runs 4 · schedule 3 · bench_runs 3`."""
    return " · ".join(f"{table} {count}" for table, count in row_counts.items())


def labelled(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
