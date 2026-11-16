"""`cstudy lang` (docs/specs/cli.md#cstudy-lang): list, add and remove the workspace's languages."""

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.ide.generated_files import FsGeneratedFiles
from coding_study.adapters.language_folders import FsLanguageFolders
from coding_study.adapters.locations import find_workspace
from coding_study.adapters.run_activity import ProcessRunActivity
from coding_study.adapters.workspace_marker import read_marker
from coding_study.adapters.workspace_setup import FsWorkspaceLanguageStore
from coding_study.application.environment import Environment
from coding_study.application.ide_files import IdeReport, refresh_written_ides
from coding_study.application.workspace_languages import (
    FolderPreview,
    FolderState,
    LanguageChange,
    LanguageRequest,
    change_languages,
    language_removal_preview,
)
from coding_study.domain.errors import FolderNotDeletedError, UsageError
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
NEEDS_A_TERMINAL = (
    "cstudy lang remove --delete-folder asks before it deletes; in a script, pass --yes"
)
NOT_REMOVED = "not removed: nothing changed"
STAYS = "progress, .archive/, projects/ and notes/"
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


def remove(
    context: typer.Context,
    languages: Annotated[list[str], LANGUAGES_ARGUMENT],
    delete_folder: Annotated[
        bool,
        typer.Option(
            "--delete-folder",
            help="Also delete the language's folder, after a question; default: keep it.",
        ),
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", help="Do not ask: for a shell with no one to answer.")
    ] = False,
) -> None:
    """Remove languages from the workspace; their folders stay unless asked."""
    chosen = _chosen(languages)
    environment = _environment(context)
    output = console(context)
    if delete_folder:
        plan = language_removal_preview(
            environment,
            FsLanguageFolders(environment.root),
            ProcessRunActivity(environment.root),
            chosen,
        )
        if any(folder.state is not FolderState.ABSENT for folder in plan.folders):
            for line in _preview_lines(plan.folders):
                output.print(line)
        if plan.present and not (yes or _confirmed(plan.present)):
            output.print(Text(NOT_REMOVED))
            return
    request = LanguageRequest(remove=chosen, delete_folders=delete_folder)
    change = _change(environment, request)
    for line in _remove_lines(change, delete_folder):
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
    """The change. A folder that stays in part exits 4 after the marker changed, so the IDE files
    follow the languages before the error does."""
    root = environment.root
    try:
        return change_languages(
            environment,
            FsWorkspaceLanguageStore(root),
            FsLanguageFolders(root),
            ProcessRunActivity(root),
            request,
        )
    except FolderNotDeletedError:
        _refresh_ide_files(root)
        raise


def _refresh_ide_files(root: Path) -> IdeReport | None:
    return refresh_written_ides(RENDERERS, FsGeneratedFiles(root))


def _ide_lines(root: Path) -> Iterator[Text]:
    report = _refresh_ide_files(root)
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
    folders = _folders(change.added)
    yield _line("files", f"{folders}: {written} written, {kept} kept")


def _remove_lines(change: LanguageChange, deleted: bool) -> Iterator[Text]:
    plan = change.removal
    assert plan is not None
    for language in plan.not_listed:
        yield Text(f"{language.value} is not one of this workspace's languages")
    if plan.listed:
        yield _line("removed", _names(plan.listed))
    for folder in plan.folders:
        if not set(folder.removed) & set(plan.listed) and not deleted:
            continue
        match folder.state:
            case FolderState.PRESENT if deleted:
                yield _line("deleted", f"{folder.text} ({_files(folder.practice_files)})")
            case FolderState.PRESENT:
                yield _line("kept", f"{folder.text} ({_delete_hint(folder)})")
            case FolderState.ABSENT if deleted:
                yield Text(f"{folder.text} is not there")
            case _:
                pass
    if not deleted:
        for attempt in plan.attempts:
            if attempt.language in plan.listed:
                where = f"{attempt.slug}, {attempt.language}"
                yield _line("note", f"attempt {attempt.id} ({where}) is in progress")


def _preview_lines(folders: tuple[FolderPreview, ...]) -> Iterator[Text]:
    for folder in folders:
        match folder.state:
            case FolderState.PRESENT:
                yield _line("delete", f"{folder.text} ({_files(folder.practice_files)})")
            case FolderState.IN_USE:
                yield _line("keep", f"{folder.text}: {_names(folder.users)} still uses it")
            case FolderState.ABSENT:
                pass
    yield _line("stays", STAYS)


def _confirmed(present: tuple[FolderPreview, ...]) -> bool:
    """Asks whether to delete `present`. Raises UsageError when there is no one to ask."""
    if not _is_terminal():
        raise UsageError(NEEDS_A_TERMINAL)
    names = folder_text(path for folder in present for path in folder.paths)
    count = sum(folder.practice_files for folder in present)
    whose = "Its" if len(present) == 1 else "Their"
    return typer.confirm(
        f"Delete {names}? {whose} {_files(count)} can't be recovered.", default=False
    )


def _is_terminal() -> bool:
    return sys.stdin.isatty()


def _delete_hint(folder: FolderPreview) -> str:
    return f"cstudy lang remove {_names(folder.removed, ' ')} --delete-folder deletes it"


def _files(count: int) -> str:
    return f"{count} practice file{'' if count == 1 else 's'}"


def _names(languages: tuple[Language, ...], separator: str = ", ") -> str:
    return separator.join(language.value for language in languages)


def _folders(languages: tuple[Language, ...]) -> str:
    return folder_text(path for paths in folder_groups(languages) for path in paths)


def _line(label: str, value: str) -> Text:
    return Text(f"{label.ljust(LABEL_WIDTH)}{value}")
