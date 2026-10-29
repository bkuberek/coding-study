"""`cstudy list` (docs/specs/cli.md#cstudy-list)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_catalog_environment
from coding_study.application.list_items import ListedItem, list_items
from coding_study.application.list_problems import ListedProblem, ProblemFilter, list_problems
from coding_study.domain.problem import ContentStatus, Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemStatus
from coding_study.domain.value_text import truncate
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "list"
COLUMN_GAP = 2
ID_WIDTH = 4
SLUG_WIDTH = 16
DIFFICULTY_WIDTH = 6
PATTERN_WIDTH = 15
STATUS_WIDTH = 8
DUE_WIDTH = 10
NO_VALUE = "-"
NO_MATCH = "no problems match"
REFERENCE_LABELS = {
    Language.PYTHON: "py",
    Language.TYPESCRIPT: "ts",
    Language.JAVA: "java",
    Language.KOTLIN: "kt",
    Language.GO: "go",
    Language.RUST: "rs",
}
_WIDTHS = (ID_WIDTH, SLUG_WIDTH, DIFFICULTY_WIDTH, PATTERN_WIDTH, STATUS_WIDTH, DUE_WIDTH)
_HEADER = ("ID", "SLUG", "DIFF", "PATTERN", "STATUS", "DUE", "REFS")


def register(app: typer.Typer) -> None:
    add_command(app, list_command, NAME)


def list_command(
    context: typer.Context,
    track: Annotated[Track | None, typer.Option("--track", help="Only this track.")] = None,
    pattern: Annotated[
        str | None, typer.Option("--pattern", help="Problems that list this pattern.")
    ] = None,
    difficulty: Annotated[
        Difficulty | None, typer.Option("--difficulty", help="Only this difficulty.")
    ] = None,
    status: Annotated[
        ProblemStatus | None, typer.Option("--status", help="Only problems in this status.")
    ] = None,
    content: Annotated[
        ContentStatus | None, typer.Option("--content", help="Content status: draft or ready.")
    ] = None,
    language: Annotated[
        Language | None, typer.Option("--lang", help="Problems with a reference in it.")
    ] = None,
) -> None:
    """Browse problems with filters."""
    problem_filter = ProblemFilter(track, pattern, difficulty, status, content, language)
    environment = load_catalog_environment(Path.cwd(), command_environ(context), Path.home())
    rows = [_cells(item) for item in list_problems(environment, problem_filter)]
    rows += [_item_cells(item) for item in list_items(environment, problem_filter)]
    output = console(context)
    if not rows:
        output.print(NO_MATCH)
        return
    output.print(Text(_row(_HEADER), style="bold"))
    for cells in rows:
        output.print(Text(_row(cells)))


def _cells(item: ListedProblem) -> tuple[str, ...]:
    meta = item.summary.meta
    references = " ".join(
        REFERENCE_LABELS[language] for language in item.summary.reference_languages
    )
    return (
        meta.id,
        meta.slug,
        meta.difficulty,
        meta.patterns[0] if meta.patterns else NO_VALUE,
        item.status,
        item.due_on.isoformat() if item.due_on else NO_VALUE,
        references or NO_VALUE,
    )


def _item_cells(item: ListedItem) -> tuple[str, ...]:
    """Items have no id, pattern or references; their track takes the pattern column."""
    meta = item.meta
    due = item.due_on.isoformat() if item.due_on else NO_VALUE
    return (NO_VALUE, meta.slug, meta.difficulty, meta.track, item.status, due, NO_VALUE)


def _row(cells: tuple[str, ...]) -> str:
    padded = (
        _fit(cell, width).ljust(width + COLUMN_GAP)
        for cell, width in zip(cells, _WIDTHS, strict=False)
    )
    return "".join(padded) + cells[-1]


def _fit(cell: str, width: int) -> str:
    """A value too long for its column ends in "..." one character short of the column."""
    return cell if len(cell) <= width else truncate(cell, width - 1)
