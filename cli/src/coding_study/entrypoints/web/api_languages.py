"""The workspace's languages, as `cstudy lang` lists, adds and removes them: `GET` and `POST
/api/v1/languages`, and the preview of a deletion, `GET /api/v1/languages/removal`
(docs/specs/web-ui.md#session-and-preferences). A removal keeps the language's folder unless the
body says `delete_folders` and, once the preview is shown, `confirm`."""

from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.adapters.ide.generated_files import FsGeneratedFiles
from coding_study.adapters.language_folders import FsLanguageFolders
from coding_study.adapters.run_activity import ProcessRunActivity
from coding_study.adapters.workspace_marker import MarkerError
from coding_study.adapters.workspace_setup import FsWorkspaceLanguageStore
from coding_study.application.environment import Environment
from coding_study.application.ide_files import IdeReport, refresh_written_ides
from coding_study.application.workspace_languages import (
    FolderPreview,
    FolderState,
    LanguageChange,
    LanguageRequest,
    RemovalPlan,
    attempt_refusal,
    change_languages,
    language_removal_preview,
    removal_plan,
    workspace_languages,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import FolderNotDeletedError, UsageError
from coding_study.domain.ide import Change
from coding_study.domain.problem import Language
from coding_study.domain.workspace_languages import (
    WorkspaceLanguageError,
    choose,
    folder_groups,
    folder_names,
)
from coding_study.entrypoints.commands.ide import RENDERERS
from coding_study.entrypoints.commands.lang import (
    STAYS_PATHS,
    attempt_note,
    delete_question,
    still_uses,
)
from coding_study.entrypoints.web.bodies import Body, object_body, switch, text_list
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.queries import choice_list
from coding_study.entrypoints.web.responses import JsonResponse

LANGUAGES = "/api/v1/languages"
REMOVAL = f"{LANGUAGES}/removal"
REMOVE_COMMAND = "cstudy lang remove"
IDE_CHANGES = (Change.CREATED, Change.UPDATED, Change.REMOVED)
"""What `ide` lists of a change: the files cstudy wrote, rewrote or took away."""


async def list_languages(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _languages))


async def removal(request: Request) -> Response:
    """What a deletion of the languages' folders would delete, keep and leave alone. It changes
    nothing, and waits as the change does while a run or a job is active."""
    languages = _asked(request.query_params)
    async with server_state(request).children.none_running(REMOVE_COMMAND):
        return JsonResponse(await in_workspace(request, _removal, languages))


async def change(request: Request) -> Response:
    """`cstudy lang add` and `cstudy lang remove` in one request, adds first. A deletion needs
    `confirm`, and holds off runs and jobs while it deletes."""
    body = await object_body(request)
    asked = LanguageRequest(
        add=_languages_of(body, "add"),
        remove=_languages_of(body, "remove"),
        delete_folders=switch(body, "delete_folders"),
    )
    confirmed = switch(body, "confirm")
    if not (asked.delete_folders and asked.remove):
        return JsonResponse(await in_workspace(request, _change, asked, confirmed))
    async with server_state(request).children.none_running(REMOVE_COMMAND):
        return JsonResponse(await in_workspace(request, _change, asked, confirmed))


def language_routes() -> list[BaseRoute]:
    return [
        Route(LANGUAGES, list_languages, methods=["GET"]),
        Route(REMOVAL, removal, methods=["GET"]),
        Route(LANGUAGES, change, methods=["POST"]),
    ]


def _asked(query: QueryParams) -> tuple[Language, ...]:
    """The `language` parameters, each once in workspace order; at least one."""
    if not query.getlist("language"):
        raise UsageError("the request needs language")
    return choose(choice_list(query, "language", Language))


def _languages_of(body: Body, name: str) -> tuple[Language, ...]:
    try:
        return choose(text_list(body, name))
    except WorkspaceLanguageError as error:
        raise UsageError(str(error)) from None


def _languages(environment: Environment) -> dict[str, JsonValue]:
    """What `cstudy lang list` prints, as values."""
    languages = workspace_languages(environment)
    return {
        "languages": [language.value for language in languages],
        "chosen": environment.workspace_languages is not None,
        "folders": list(_folders(languages)),
    }


def _folders(languages: tuple[Language, ...]) -> tuple[str, ...]:
    return folder_names(path for paths in folder_groups(languages) for path in paths)


def _removal(environment: Environment, languages: tuple[Language, ...]) -> dict[str, JsonValue]:
    """The plan, after the checks that refuse a deletion; an attempt in progress is `blocked`
    instead of an error, so the page can name it."""
    folders = FsLanguageFolders(environment.root)
    plan = removal_plan(environment, folders, languages)
    if not plan.attempts:
        activity = ProcessRunActivity(environment.root)
        plan = language_removal_preview(environment, folders, activity, languages)
    return {
        "delete": [_deleted(folder) for folder in plan.present],
        "keep": [
            {"path": folder.text, "reason": still_uses(folder)}
            for folder in plan.folders
            if folder.state is FolderState.IN_USE
        ],
        "stays": list(STAYS_PATHS),
        "blocked": [attempt_refusal(attempt) for attempt in plan.attempts],
    }


def _deleted(folder: FolderPreview) -> JsonValue:
    return {"path": folder.text, "files": folder.practice_files}


def _change(
    environment: Environment, asked: LanguageRequest, confirmed: bool
) -> dict[str, JsonValue]:
    """Without `confirm`, a deletion that would delete something changes nothing and asks its
    question. The IDE files follow the languages, even when a folder stays in part."""
    root = environment.root
    folders = FsLanguageFolders(root)
    activity = ProcessRunActivity(root)
    if asked.delete_folders and asked.remove:
        plan = language_removal_preview(environment, folders, activity, asked.remove, asked.add)
        if plan.present and not confirmed:
            raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, delete_question(plan.present))
    try:
        changed = change_languages(
            environment, FsWorkspaceLanguageStore(root), folders, activity, asked
        )
    except MarkerError as error:
        raise ApiError(ErrorCode.ENVIRONMENT, str(error)) from None
    except FolderNotDeletedError:
        _refresh_ide_files(environment)
        raise
    return _changed_document(environment, changed, _refresh_ide_files(environment))


def _refresh_ide_files(environment: Environment) -> IdeReport | None:
    return refresh_written_ides(RENDERERS, FsGeneratedFiles(environment.root))


def _changed_document(
    environment: Environment, changed: LanguageChange, ide: IdeReport | None
) -> dict[str, JsonValue]:
    plan = changed.removal
    return {
        "languages": [language.value for language in changed.languages],
        "chosen": environment.workspace_languages is not None
        or changed.languages != workspace_languages(environment),
        "added": [language.value for language in changed.added],
        "removed": [language.value for language in plan.listed] if plan else [],
        "written": list(changed.files.written) if changed.files else [],
        "kept": list(changed.files.kept) if changed.files else [],
        "deleted": [_deleted(folder) for folder in changed.deleted],
        "ide": [path for change in IDE_CHANGES for path in ide.paths(change)] if ide else [],
        "notes": _notes(plan),
    }


def _notes(plan: RemovalPlan | None) -> list[JsonValue]:
    """One per attempt in progress in a removed language, which a removal that keeps the folder
    leaves running; a deletion is refused while one is."""
    if plan is None:
        return []
    return [attempt_note(attempt) for attempt in plan.attempts if attempt.language in plan.listed]
