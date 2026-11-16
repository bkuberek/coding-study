"""`cstudy lang` (docs/specs/cli.md#cstudy-lang): list, add and remove the workspace's languages."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.ide.generated_files import FsGeneratedFiles
from coding_study.adapters.locations import find_workspace
from coding_study.adapters.workspace_marker import read_marker
from coding_study.adapters.workspace_setup import FsWorkspaceLanguageStore
from coding_study.application.environment import Environment
from coding_study.application.ide_files import refresh_written_ides
from coding_study.application.workspace_languages import (
    FolderPreview,
    FolderState,
    LanguageChange,
    LanguageRequest,
    change_languages,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import ALL_LANGUAGES, Language
from coding_study.domain.workspace_languages import (
    WorkspaceLanguageError,
    choose,
    folder_groups,
    folder_text,
)
from coding_study.entrypoints.commands.ide import RENDERERS, report_lines
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "lang"
LABEL_WIDTH = 11
ADD_HINT = "cstudy lang add <language>"
NEXT_STEP = "cstudy doctor --fix"
LANGUAGES_ARGUMENT = typer.Argument(help="python, typescript, java, kotlin, go or rust.")


def register(app: typer.Typer) -> None:
    group = typer.Typer(
        help="List, add or remove the languages of your workspace.", no_args_is_help=True
    )
    add_command(group, list_languages, "list")
    add_command(group, add, "add")
    add_command(group, remove, "remove")
    app.add_typer(group, name=NAME)


def list_languages(context: typer.Context) -> None:
    """Show the workspace's languages and their folders."""
    marker = read_marker(find_workspace(Path.cwd(), command_environ(context)))
    languages = marker.languages or ALL_LANGUAGES
    output = console(context)
    if marker.languages is None:
        output.print(_line("languages", "all six (none chosen; cstudy lang remove narrows them)"))
    else:
        output.print(_line("languages", _names(languages)))
    output.print(_line("folders", _folders(languages)))
    if len(languages) < len(ALL_LANGUAGES):
        output.print(_line("add", ADD_HINT))


def add(context: typer.Context, languages: Annotated[list[str], LANGUAGES_ARGUMENT]) -> None:
    """Add languages to the workspace and write their folders."""
    chosen = _chosen(languages)
    environment = _environment(context)
    change = _change(environment, LanguageRequest(add=chosen))
    output = console(context)
    for line in _add_lines(change, environment.workspace_languages is None):
        output.print(line)
    for line in _ide_lines(environment.root):
        output.print(line)
    if change.added:
        output.print(_line("next", NEXT_STEP))


def remove(context: typer.Context, languages: Annotated[list[str], LANGUAGES_ARGUMENT]) -> None:
    """Remove languages from the workspace; their folders stay."""
    chosen = _chosen(languages)
    environment = _environment(context)
    change = _change(environment, LanguageRequest(remove=chosen))
    output = console(context)
    for line in _remove_lines(change):
        output.print(line)
    for line in _ide_lines(environment.root):
        output.print(line)


def _chosen(names: list[str]) -> tuple[Language, ...]:
    """The language arguments, each once in workspace order. Raises UsageError for an unknown
    name, before anything is read or written."""
    try:
        return choose(names)
    except WorkspaceLanguageError as error:
        raise UsageError(str(error)) from None


def _environment(context: typer.Context) -> Environment:
    return load_environment(Path.cwd(), command_environ(context), Path.home())


def _change(environment: Environment, request: LanguageRequest) -> LanguageChange:
    store = FsWorkspaceLanguageStore(environment.root)
    return change_languages(environment, store, request)


def _ide_lines(root: Path) -> Iterator[Text]:
    """The `ide` line of the IDE files that follow the languages, when one changed."""
    report = refresh_written_ides(RENDERERS, FsGeneratedFiles(root))
    if report is not None and report.changed:
        yield from report_lines(report, LABEL_WIDTH)


def _add_lines(change: LanguageChange, unchosen: bool) -> Iterator[Text]:
    suffix = " (it has all six)" if unchosen else ""
    for language in change.already:
        yield Text(f"{language.value} is already one of this workspace's languages{suffix}")
    if not change.added:
        return
    yield _line("added", _names(change.added))
    assert change.files is not None
    written, kept = len(change.files.written), len(change.files.kept)
    yield _line("files", f"{_folders(change.added)}: {written} written, {kept} kept")


def _remove_lines(change: LanguageChange) -> Iterator[Text]:
    plan = change.removal
    assert plan is not None
    for language in plan.not_listed:
        yield Text(f"{language.value} is not one of this workspace's languages")
    if plan.listed:
        yield _line("removed", _names(plan.listed))
    for folder in plan.folders:
        if folder.state is FolderState.PRESENT and set(folder.removed) & set(plan.listed):
            yield _line("kept", f"{folder.text} ({_delete_hint(folder)})")
    for attempt in plan.attempts:
        if attempt.language in plan.listed:
            where = f"{attempt.slug}, {attempt.language}"
            yield _line("note", f"attempt {attempt.id} ({where}) is in progress")


def _delete_hint(folder: FolderPreview) -> str:
    return f"cstudy lang remove {_names(folder.removed, ' ')} --delete-folder deletes it"


def _names(languages: tuple[Language, ...], separator: str = ", ") -> str:
    return separator.join(language.value for language in languages)


def _folders(languages: tuple[Language, ...]) -> str:
    return folder_text(path for paths in folder_groups(languages) for path in paths)


def _line(label: str, value: str) -> Text:
    return Text(f"{label.ljust(LABEL_WIDTH)}{value}")
