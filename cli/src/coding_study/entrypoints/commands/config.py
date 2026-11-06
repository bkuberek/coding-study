"""`cstudy config` (docs/specs/cli.md#cstudy-config): where the user's config file is, and opening
it in their editor. Neither needs a workspace."""

from collections.abc import Mapping
from pathlib import Path

import typer
from rich.text import Text

from coding_study.adapters.env_editor import EnvEditorOpener
from coding_study.adapters.locations import workspace_directory
from coding_study.adapters.toml_config import TomlConfigSource, config_path
from coding_study.adapters.workspace_marker import has_marker
from coding_study.application.open_config import ProgressDbChange, open_config
from coding_study.application.progress_db_change import progress_db_notice
from coding_study.entrypoints.commands.export import labelled
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "config"


def register(app: typer.Typer) -> None:
    group = typer.Typer(help="Find or edit your config.toml.", no_args_is_help=True)
    add_command(group, edit, "edit")
    add_command(group, path, "path")
    app.add_typer(group, name=NAME)


def edit(context: typer.Context) -> None:
    """Open your config.toml in $VISUAL or $EDITOR, creating it when missing."""
    environ = command_environ(context)
    source = TomlConfigSource(config_path(environ, Path.home()))
    opened = open_config(source, EnvEditorOpener(environ))
    output = console(context)
    output.print(labelled("created" if opened.created else "config", source.location))
    if opened.editor_problem is not None:
        output.print(labelled("editor", opened.editor_problem))
    if opened.progress_db is not None:
        output.print(labelled("progress_db", _notice(opened.progress_db, environ)))


def _notice(change: ProgressDbChange, environ: Mapping[str, str]) -> str:
    workspace = workspace_directory(Path.cwd(), environ)
    is_there = (workspace / change.new).exists() if has_marker(workspace) else None
    return progress_db_notice(change.current, change.new, is_there)


def path(context: typer.Context) -> None:
    """Print the path of your config.toml."""
    location = config_path(command_environ(context), Path.home())
    console(context).print(Text(str(location)))
