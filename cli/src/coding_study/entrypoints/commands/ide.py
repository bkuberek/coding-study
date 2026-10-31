"""`cstudy ide` (docs/specs/cli.md#cstudy-ide)."""

from collections.abc import Iterator, Mapping
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.ide.generated_files import FsGeneratedFiles
from coding_study.adapters.ide.intellij import IntellijProject
from coding_study.adapters.ide.launcher import IdeLauncher
from coding_study.adapters.ide.vscode import VsCodeProject
from coding_study.adapters.locations import find_workspace
from coding_study.adapters.runner_runtime import RUNTIME_DIRECTORY
from coding_study.application.ide_files import (
    IdeRenderer,
    IdeReport,
    IdeRequest,
    generate_ide_files,
)
from coding_study.domain.ide import Change, Ide
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "ide"
LABEL_WIDTH = 9
"""As wide as `cstudy init`'s labels, whose report includes these lines."""
ALL_IDES = tuple(Ide)
RENDERERS: Mapping[Ide, IdeRenderer] = {Ide.VSCODE: VsCodeProject(), Ide.IDEA: IntellijProject()}


class IdeSelection(StrEnum):
    VSCODE = Ide.VSCODE.value
    IDEA = Ide.IDEA.value
    ALL = "all"

    def ides(self) -> tuple[Ide, ...]:
        return ALL_IDES if self is IdeSelection.ALL else (Ide(self.value),)


def register(app: typer.Typer) -> None:
    add_command(app, ide, NAME)


def ide(
    context: typer.Context,
    selection: Annotated[
        IdeSelection, typer.Argument(metavar="[vscode|idea|all]", help="Which IDE; default: all.")
    ] = IdeSelection.ALL,
    force: Annotated[
        bool,
        typer.Option("--force", help="Also overwrite the IDE files you edited."),
    ] = False,
) -> None:
    """Write or refresh the IDE project files and the IntelliJ launcher."""
    root = find_workspace(Path.cwd(), command_environ(context))
    IdeLauncher(root / RUNTIME_DIRECTORY).install()
    report = write_ide_files(root, IdeRequest(selection.ides(), force=force))
    output = console(context)
    for line in report_lines(report):
        output.print(line)


def write_ide_files(root: Path, request: IdeRequest) -> IdeReport:
    return generate_ide_files(RENDERERS, FsGeneratedFiles(root), request)


def report_lines(report: IdeReport, label_width: int = LABEL_WIDTH) -> Iterator[Text]:
    """`ide  vscode, idea · 2 created · 1 kept`, then a warning per kept file; labels padded to
    `label_width`, as the report that shows them pads its own."""
    counts = [
        f"{len(paths)} {change}"
        for change in Change
        if change is not Change.UNCHANGED and (paths := report.paths(change))
    ]
    summary = " · ".join(counts) if report.changed else "no changes"
    yield Text(f"{NAME.ljust(label_width)}{', '.join(report.ides)} · {summary}")
    for path in report.paths(Change.KEPT):
        yield Text(
            f"{'warning'.ljust(label_width)}kept {path}: edited, or not written by cstudy "
            f"(cstudy ide --force overwrites it)",
            style="yellow",
        )
