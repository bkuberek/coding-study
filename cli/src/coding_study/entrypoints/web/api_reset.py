"""`GET` and `POST /api/v1/reset`: the Settings view's Danger section, as `cstudy reset`
(docs/specs/cli.md#cstudy-reset). The body must hold the word, so a plain POST deletes nothing."""

from collections.abc import Iterable

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.adapters.ide.generated_files import FsGeneratedFiles
from coding_study.adapters.run_activity import ProcessRunActivity
from coding_study.application.environment import Environment
from coding_study.application.ide_files import link_rust_projects
from coding_study.application.reset_workspace import ResetRequest, reset_preview, reset_workspace
from coding_study.domain.reset import RESET_WARNING, RESET_WORD, ResetEntry, ResetPreview
from coding_study.entrypoints.commands.ide import RENDERERS
from coding_study.entrypoints.web.bodies import object_body, switch
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.responses import JsonResponse

RESET_COMMAND = "cstudy reset"


async def preview(request: Request) -> Response:
    active = server_state(request).children.active()
    found = await in_workspace(request, _preview)
    busy = found.busy if active is None else f"in progress: {active.start.title}"
    return JsonResponse(
        {
            "word": RESET_WORD,
            "warning": RESET_WARNING,
            "busy": busy,
            "kept": list(found.kept),
            "groups": [
                {
                    "option": group.option,
                    "title": group.title,
                    "entries": _entries(group.entries),
                }
                for group in found.groups
            ],
        }
    )


async def reset(request: Request) -> Response:
    server = server_state(request)
    body = await object_body(request)
    word = body.get("confirm")
    reset_request = ResetRequest(
        word if isinstance(word, str) else None, switch(body, "files"), switch(body, "archive")
    )
    async with server.children.none_running(RESET_COMMAND):
        deleted = await in_workspace(request, _reset, reset_request)
    server.notifications.progress_changed()
    return JsonResponse(
        {"deleted": [entry for group in deleted.groups for entry in _entries(group.entries)]}
    )


def reset_routes() -> list[BaseRoute]:
    return [
        Route("/api/v1/reset", preview, methods=["GET"]),
        Route("/api/v1/reset", reset, methods=["POST"]),
    ]


def _entries(entries: Iterable[ResetEntry]) -> list[dict[str, object]]:
    return [{"label": entry.label, "count": entry.count} for entry in entries]


def _preview(environment: Environment) -> ResetPreview:
    return reset_preview(environment, ProcessRunActivity(environment.root))


def _reset(environment: Environment, request: ResetRequest) -> ResetPreview:
    deleted = reset_workspace(environment, request, ProcessRunActivity(environment.root))
    if request.files:
        link_rust_projects(RENDERERS, FsGeneratedFiles(environment.root))
    return deleted
