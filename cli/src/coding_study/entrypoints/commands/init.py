"""`cstudy init` (docs/specs/installation-and-workspaces.md#cstudy-init)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import RUNNERS_DIRECTORY
from coding_study.adapters.locations import WORKSPACE_VARIABLE, find_content_root
from coding_study.adapters.workspace_marker import tool_version
from coding_study.adapters.workspace_setup import FsWorkspaceSetup
from coding_study.application.ide_files import IdeReport, IdeRequest
from coding_study.application.init_workspace import (
    InitializedWorkspace,
    InitRequest,
    init_workspace,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.ide import Ide
from coding_study.entrypoints.commands.ide import ALL_IDES, report_lines, write_ide_files
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "init"
STEP_INDENT = "  "


def register(app: typer.Typer) -> None:
    add_command(app, init, NAME)


def init(
    context: typer.Context,
    path: Annotated[
        Path | None,
        typer.Argument(
            help="Where to create it; default: --workspace, CSTUDY_WORKSPACE, or here.",
            file_okay=False,
        ),
    ] = None,
    git: Annotated[
        bool, typer.Option("--git", help="Run git init there (cstudy never commits).")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Allow a workspace inside a coding-study checkout.")
    ] = False,
    ides: Annotated[
        list[Ide] | None,
        typer.Option("--ide", help="Write this IDE's project files (repeatable); default: both."),
    ] = None,
    no_ide: Annotated[bool, typer.Option("--no-ide", help="Write no IDE project files.")] = False,
) -> None:
    """Create a workspace for your solutions, notes and progress."""
    selected = _selected_ides(ides or [], no_ide)
    environ = command_environ(context)
    target = (path or _default_target(environ)).expanduser().resolve()
    content = find_content_root(environ)
    setup = FsWorkspaceSetup(content.path / RUNNERS_DIRECTORY, tool_version())
    created = init_workspace(setup, InitRequest(target, git=git, force=force))
    ide_files = write_ide_files(target, IdeRequest(selected)) if selected else None
    output = console(context)
    for line in _report(created, ide_files, Path.cwd()):
        output.print(line)


def _selected_ides(named: list[Ide], none: bool) -> tuple[Ide, ...]:
    """`--ide` in the order given, nothing with `--no-ide`, else every IDE."""
    if named and none:
        raise UsageError("--ide and --no-ide exclude each other")
    if none:
        return ()
    return tuple(dict.fromkeys(named)) if named else ALL_IDES


def _default_target(environ: dict[str, str]) -> Path:
    """`--workspace` or CSTUDY_WORKSPACE when set, else the current directory; never a workspace
    found above it, which `cstudy init` refuses rather than reuses."""
    override = environ.get(WORKSPACE_VARIABLE, "")
    return Path.cwd() / Path(override).expanduser() if override else Path.cwd()


def _report(
    created: InitializedWorkspace, ide_files: IdeReport | None, current: Path
) -> Iterator[Text]:
    files = created.files
    yield Text(f"created workspace {created.root}", "bold")
    yield Text(f"files    {len(files.written)} written · {len(files.kept)} kept")
    if ide_files:
        yield from report_lines(ide_files)
    yield Text("next steps")
    if created.root != current:
        yield Text(f"{STEP_INDENT}cd {created.root}")
    yield Text(f"{STEP_INDENT}cstudy doctor --fix      # install the toolchains and warm Gradle")
    yield Text(f"{STEP_INDENT}cstudy start two-sum     # your first problem")
