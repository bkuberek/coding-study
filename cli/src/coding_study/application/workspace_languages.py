"""A workspace's languages, added and removed (docs/specs/cli.md#cstudy-lang): the marker's
`languages`, each language's template files, and, when asked, the deletion of a removed language's
folder (docs/specs/cli.md#deleting-a-languages-folder).

Everything that can refuse does so first, with nothing written; the marker changes next, then the
folders. The IDE files follow the languages and are the caller's: they belong to the entrypoint.
"""

from dataclasses import dataclass
from enum import StrEnum

from coding_study.application.environment import Environment
from coding_study.application.ports import (
    LanguageFolders,
    RunActivity,
    ScaffoldOutcome,
    WorkspaceLanguageStore,
)
from coding_study.application.reset_workspace import own_files
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UsageError, WorkspaceBusyError
from coding_study.domain.layout import user_directory
from coding_study.domain.problem import ALL_LANGUAGES, Language
from coding_study.domain.workspace_languages import (
    TEMPLATE_PATHS,
    folder_groups,
    folder_text,
    ordered,
    sharing,
)

LAST_LANGUAGE = "a workspace needs at least one language"


class FolderState(StrEnum):
    IN_USE = "in use"
    """A language that stays uses it: `jvm/` of Java while Kotlin stays."""
    PRESENT = "present"
    ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class FolderPreview:
    """The paths one removal puts at stake: a language's folder, or `go/` with `go.work`."""

    paths: tuple[str, ...]
    removed: tuple[Language, ...]
    """The languages of the request that own the paths."""
    state: FolderState
    practice_files: int
    """The files under the practice paths of every language that shares the paths, counted as
    `cstudy reset --files` counts them; 0 unless the folder is present."""
    users: tuple[Language, ...] = ()
    """The remaining languages that use the folder, when it is in use."""

    @property
    def text(self) -> str:
        return folder_text(self.paths)


@dataclass(frozen=True, slots=True)
class RemovalPlan:
    languages: tuple[Language, ...]
    """What the request asks to remove, in workspace order, listed or not."""
    listed: tuple[Language, ...]
    """Of them, the languages the workspace has."""
    folders: tuple[FolderPreview, ...]
    attempts: tuple[Attempt, ...]
    """The attempts in progress in a language of the request."""

    @property
    def not_listed(self) -> tuple[Language, ...]:
        return tuple(language for language in self.languages if language not in self.listed)

    @property
    def present(self) -> tuple[FolderPreview, ...]:
        """The folders a deletion would delete."""
        return tuple(folder for folder in self.folders if folder.state is FolderState.PRESENT)


@dataclass(frozen=True, slots=True)
class LanguageRequest:
    add: tuple[Language, ...] = ()
    remove: tuple[Language, ...] = ()
    delete_folders: bool = False
    """Delete the folders of the removed languages, the preview having been shown and confirmed."""


@dataclass(frozen=True, slots=True)
class LanguageChange:
    languages: tuple[Language, ...]
    """The workspace's languages afterwards."""
    added: tuple[Language, ...] = ()
    already: tuple[Language, ...] = ()
    """The languages to add that the workspace had."""
    files: ScaffoldOutcome | None = None
    """The template files of the added languages."""
    removal: RemovalPlan | None = None
    deleted: tuple[FolderPreview, ...] = ()


def workspace_languages(environment: Environment) -> tuple[Language, ...]:
    """The languages the workspace has: the marker's, or all six when it listed none."""
    return environment.workspace_languages or ALL_LANGUAGES


def removal_plan(
    environment: Environment,
    folders: LanguageFolders,
    languages: tuple[Language, ...],
    adding: tuple[Language, ...] = (),
) -> RemovalPlan:
    """What removing `languages` leaves and what is at stake, checking nothing but that a language
    stays, `adding` counted. Raises UsageError when none would."""
    asked = ordered(languages)
    current = workspace_languages(environment)
    remaining = ordered(language for language in (*current, *adding) if language not in asked)
    if not remaining:
        raise UsageError(LAST_LANGUAGE)
    previews = tuple(
        _folder_preview(environment, folders, paths, asked, remaining)
        for paths in folder_groups(asked)
    )
    listed = tuple(language for language in asked if language in current)
    attempts = tuple(
        attempt
        for attempt in environment.progress.attempts_in_progress()
        if attempt.language in asked
    )
    return RemovalPlan(asked, listed, previews, attempts)


def language_removal_preview(
    environment: Environment,
    folders: LanguageFolders,
    activity: RunActivity,
    languages: tuple[Language, ...],
    adding: tuple[Language, ...] = (),
) -> RemovalPlan:
    """What `cstudy lang remove --delete-folder` would delete, after the checks that refuse it: a
    language that would be the last, an attempt in progress in a removed language (UsageError
    naming each), a run or a job (WorkspaceBusyError) and a folder that is a link or leaves the
    workspace (UsageError). It changes nothing."""
    plan = removal_plan(environment, folders, languages, adding)
    if plan.attempts:
        raise UsageError("\n".join(_attempt_refusal(attempt) for attempt in plan.attempts))
    busy = activity.active_run()
    if busy is not None:
        raise WorkspaceBusyError(f"cstudy lang remove waits until it ends: {busy}")
    for folder in plan.present:
        for path in folder.paths:
            if folders.present(path) and folders.leaves_workspace(path):
                raise UsageError(
                    f"{path} leaves the workspace, so cstudy lang remove deleted nothing; "
                    "remove the link first"
                )
    return plan


def change_languages(
    environment: Environment,
    store: WorkspaceLanguageStore,
    folders: LanguageFolders,
    activity: RunActivity,
    request: LanguageRequest,
) -> LanguageChange:
    """Adds and removes languages: the marker first, then the added languages' missing template
    files, then, with `request.delete_folders`, the removed languages' folders. A removal that
    deletes is checked as `language_removal_preview` does before anything is written. Raises
    UsageError and WorkspaceBusyError for a refusal, with nothing changed, and
    FolderNotDeletedError for a folder that stays in part."""
    overlap = set(request.add) & set(request.remove)
    if overlap:
        names = ", ".join(language.value for language in ordered(overlap))
        raise UsageError(f"cannot add and remove {names} in one change")
    current = workspace_languages(environment)
    removal = None
    if request.remove:
        removal = (
            language_removal_preview(environment, folders, activity, request.remove, request.add)
            if request.delete_folders
            else removal_plan(environment, folders, request.remove, request.add)
        )
    added = tuple(language for language in ordered(request.add) if language not in current)
    already = tuple(language for language in ordered(request.add) if language in current)
    removed = removal.listed if removal is not None else ()
    languages = ordered((*(language for language in current if language not in removed), *added))
    if languages != current:
        store.write_languages(languages)
    files = store.write_language_files(added) if added else None
    deleted: tuple[FolderPreview, ...] = ()
    if removal is not None and request.delete_folders:
        deleted = removal.present
        for folder in deleted:
            for path in folder.paths:
                folders.delete(path)
    return LanguageChange(languages, added, already, files, removal, deleted)


def _folder_preview(
    environment: Environment,
    folders: LanguageFolders,
    paths: tuple[str, ...],
    asked: tuple[Language, ...],
    remaining: tuple[Language, ...],
) -> FolderPreview:
    owners = sharing(paths)
    removed = tuple(language for language in owners if language in asked)
    users = tuple(language for language in owners if language in remaining)
    if users:
        return FolderPreview(paths, removed, FolderState.IN_USE, 0, users)
    if not any(folders.present(path) for path in paths):
        return FolderPreview(paths, removed, FolderState.ABSENT, 0)
    practice = tuple(dict.fromkeys(user_directory(language) for language in owners))
    count = own_files(environment.workspace, *practice)
    return FolderPreview(paths, removed, FolderState.PRESENT, count)


def _attempt_refusal(attempt: Attempt) -> str:
    assert attempt.language is not None
    folder = folder_text(TEMPLATE_PATHS[attempt.language])
    language = attempt.language.value
    return (
        f"cannot delete {folder}: attempt {attempt.id} ({attempt.slug}, {language}) is in "
        f"progress; finish it with cstudy done or end it with cstudy abort, or remove "
        f"{language} without --delete-folder"
    )
