"""A workspace's languages, added and removed (docs/specs/cli.md#cstudy-lang): the marker's
`languages` and each language's template files. A removed language's folder stays.

The IDE files follow the languages and are the caller's: they belong to the entrypoint.
"""

from dataclasses import dataclass
from enum import StrEnum

from coding_study.application.environment import Environment
from coding_study.application.ports import ScaffoldOutcome, WorkspaceLanguageStore
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import ALL_LANGUAGES, Language
from coding_study.domain.workspace_languages import folder_groups, folder_text, ordered, sharing

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


@dataclass(frozen=True, slots=True)
class LanguageRequest:
    add: tuple[Language, ...] = ()
    remove: tuple[Language, ...] = ()


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


def workspace_languages(environment: Environment) -> tuple[Language, ...]:
    """The languages the workspace has: the marker's, or all six when it listed none."""
    return environment.workspace_languages or ALL_LANGUAGES


def removal_plan(
    environment: Environment,
    languages: tuple[Language, ...],
    adding: tuple[Language, ...] = (),
) -> RemovalPlan:
    """What removing `languages` leaves and what is at stake, `adding` counted. Raises UsageError
    when no language would stay."""
    asked = ordered(languages)
    current = workspace_languages(environment)
    remaining = ordered(language for language in (*current, *adding) if language not in asked)
    if not remaining:
        raise UsageError(LAST_LANGUAGE)
    previews = tuple(
        _folder_preview(environment, paths, asked, remaining) for paths in folder_groups(asked)
    )
    listed = tuple(language for language in asked if language in current)
    attempts = tuple(
        attempt
        for attempt in environment.progress.attempts_in_progress()
        if attempt.language in asked
    )
    return RemovalPlan(asked, listed, previews, attempts)


def change_languages(
    environment: Environment, store: WorkspaceLanguageStore, request: LanguageRequest
) -> LanguageChange:
    """Adds and removes languages: the marker first, then the added languages' missing template
    files. A removed language's folder, practice files and progress stay. Raises UsageError, with
    nothing changed, when the request would leave no language or names a language twice."""
    overlap = set(request.add) & set(request.remove)
    if overlap:
        names = ", ".join(language.value for language in ordered(overlap))
        raise UsageError(f"cannot add and remove {names} in one change")
    current = workspace_languages(environment)
    removal = removal_plan(environment, request.remove, request.add) if request.remove else None
    added = tuple(language for language in ordered(request.add) if language not in current)
    already = tuple(language for language in ordered(request.add) if language in current)
    removed = removal.listed if removal is not None else ()
    languages = ordered((*(language for language in current if language not in removed), *added))
    if languages != current:
        store.write_languages(languages)
    files = store.write_language_files(added) if added else None
    return LanguageChange(languages, added, already, files, removal)


def _folder_preview(
    environment: Environment,
    paths: tuple[str, ...],
    asked: tuple[Language, ...],
    remaining: tuple[Language, ...],
) -> FolderPreview:
    owners = sharing(paths)
    removed = tuple(language for language in owners if language in asked)
    users = tuple(language for language in owners if language in remaining)
    if users:
        return FolderPreview(paths, removed, FolderState.IN_USE, users)
    if not any(environment.workspace.exists(path) for path in paths):
        return FolderPreview(paths, removed, FolderState.ABSENT)
    return FolderPreview(paths, removed, FolderState.PRESENT)
