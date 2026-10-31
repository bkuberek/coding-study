"""An attempt in progress: its `cstudy status` document, its file tree and its files
(docs/specs/web-ui.md#attempts, docs/specs/web-ui.md#file-api-rules). An attempt is addressed by
its id; one that ended, or that another attempt replaced, gets 409 `attempt_ended`."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.active_attempt import attempt_in_progress
from coding_study.application.attempt_files import FileContent, attempt_tree, read_attempt_file
from coding_study.application.attempt_status import attempt_status
from coding_study.application.environment import Environment
from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.commands.status import status_document
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.documents import file_document, tree_document
from coding_study.entrypoints.web.responses import JsonResponse

ATTEMPT = "/api/v1/attempts/{attempt_id:int}"
RAW = "raw"
BYTES = "application/octet-stream"


async def status(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _status, _attempt_id(request)))


async def tree(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _tree, _attempt_id(request)))


async def read_file(request: Request) -> Response:
    """The file's document, or its bytes with `?raw`; the `ETag` is its SHA-256 either way."""
    path: str = request.path_params["path"]
    content = await in_workspace(request, _content, _attempt_id(request), path)
    headers = {"etag": f'"{content.sha256}"'}
    if RAW in request.query_params:
        return Response(content.content, media_type=BYTES, headers=headers)
    return JsonResponse(file_document(content), headers=headers)


def attempt_routes() -> list[BaseRoute]:
    return [
        Route(ATTEMPT, status, methods=["GET"]),
        Route(f"{ATTEMPT}/files", tree, methods=["GET"]),
        Route(f"{ATTEMPT}/files/{{path:path}}", read_file, methods=["GET"]),
    ]


def _attempt_id(request: Request) -> int:
    return request.path_params["attempt_id"]


def _status(environment: Environment, attempt_id: int) -> dict[str, JsonValue]:
    attempt = attempt_in_progress(environment.progress, attempt_id)
    return status_document(attempt_status(environment, attempt.slug, attempt.language))


def _tree(environment: Environment, attempt_id: int) -> dict[str, JsonValue]:
    attempt = attempt_in_progress(environment.progress, attempt_id)
    return tree_document(attempt_tree(environment, attempt))


def _content(environment: Environment, attempt_id: int, path: str) -> FileContent:
    attempt = attempt_in_progress(environment.progress, attempt_id)
    return read_attempt_file(environment, attempt, path)
