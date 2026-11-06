"""`cstudy reset` (docs/specs/cli.md#cstudy-reset): deletes progress and what is derived from it,
after a preview and the typed word."""

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.ide.generated_files import FsGeneratedFiles
from coding_study.adapters.run_activity import ProcessRunActivity
from coding_study.application.ide_files import link_rust_projects
from coding_study.application.reset_workspace import ResetRequest, reset_preview, reset_workspace
from coding_study.domain.errors import UsageError
from coding_study.domain.reset import RESET_WARNING, RESET_WORD, ResetOption, ResetPreview
from coding_study.entrypoints.commands.ide import RENDERERS
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "reset"
LABEL_WIDTH = 24
NEEDS_A_TERMINAL = "cstudy reset asks you to type a word; in a script, pass --yes"
WRONG_WORD = "that is not the word; nothing was deleted"
OPTION_FLAGS = {ResetOption.FILES: "--files", ResetOption.ARCHIVE: "--archive"}


def register(app: typer.Typer) -> None:
    add_command(app, reset, NAME)


def reset(
    context: typer.Context,
    files: Annotated[
        bool,
        typer.Option("--files", help="Also delete practice files, project folders and notes."),
    ] = False,
    archive: Annotated[
        bool, typer.Option("--archive", help="Also delete .archive/, earlier attempts' files.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", help="Do not ask: for a shell with no one to type.")
    ] = False,
) -> None:
    """Delete progress and state, after a preview. This can't be undone."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    activity = ProcessRunActivity(environment.root)
    output = console(context)
    chosen = {ResetOption.FILES: files, ResetOption.ARCHIVE: archive}
    _print_preview(output, reset_preview(environment, activity), chosen)
    word = RESET_WORD if yes else _asked_word(output)
    request = ResetRequest(word, files, archive)
    deleted = reset_workspace(environment, request, activity)
    if files:
        link_rust_projects(RENDERERS, FsGeneratedFiles(environment.root))
    done = [f"{entry.label} {entry.count}" for group in deleted.groups for entry in group.entries]
    output.print(Text(f"deleted {' · '.join(done)}"))


def _asked_word(output: Console) -> str:
    if not _is_terminal():
        raise UsageError(NEEDS_A_TERMINAL)
    output.print(Text(RESET_WARNING))
    word = typer.prompt(f"Type {RESET_WORD} to confirm", default="", show_default=False)
    if word != RESET_WORD:
        raise UsageError(WRONG_WORD)
    return word


def _is_terminal() -> bool:
    return sys.stdin.isatty()


def _print_preview(output: Console, preview: ResetPreview, chosen: dict[ResetOption, bool]) -> None:
    for group in preview.groups:
        deleted = group.option is None or chosen[group.option]
        heading = "deletes" if deleted else f"keeps, without {OPTION_FLAGS[group.option]}"  # type: ignore[index]
        output.print(Text(f"{heading}: {group.title}"))
        for entry in group.entries:
            output.print(Text(f"  {entry.label.ljust(LABEL_WIDTH)}{entry.count}"))
    output.print(Text("keeps"))
    for kept in preview.kept:
        output.print(Text(f"  {kept}"))
    if preview.busy is not None:
        output.print(Text(preview.busy))
