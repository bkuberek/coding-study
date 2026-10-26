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
from coding_study.application.init_workspace import (
    InitializedWorkspace,
    InitRequest,
    init_workspace,
)
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
) -> None:
    """Create a workspace for your solutions, notes and progress."""
    environ = command_environ(context)
    target = (path or _default_target(environ)).expanduser().resolve()
    content = find_content_root(environ)
    setup = FsWorkspaceSetup(content.path / RUNNERS_DIRECTORY, tool_version())
    created = init_workspace(setup, InitRequest(target, git=git, force=force))
    output = console(context)
    for line in _report(created, Path.cwd()):
        output.print(line)


def _default_target(environ: dict[str, str]) -> Path:
    """`--workspace` or CSTUDY_WORKSPACE when set, else the current directory; never a workspace
    found above it, which `cstudy init` refuses rather than reuses."""
    override = environ.get(WORKSPACE_VARIABLE, "")
    return Path.cwd() / Path(override).expanduser() if override else Path.cwd()


def _report(created: InitializedWorkspace, current: Path) -> Iterator[Text]:
    files = created.files
    yield Text(f"created workspace {created.root}", "bold")
    yield Text(f"files    {len(files.written)} written · {len(files.kept)} kept")
    yield Text("next steps")
    if created.root != current:
        yield Text(f"{STEP_INDENT}cd {created.root}")
    yield Text(f"{STEP_INDENT}cstudy doctor --fix      # install the toolchains and warm Gradle")
    yield Text(f"{STEP_INDENT}cstudy start two-sum     # your first problem")
