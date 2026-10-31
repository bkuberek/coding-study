"""Changes to an attempt's files from the page (docs/specs/web-ui.md#attempts,
docs/specs/web-ui.md#file-api-rules).

A save, a move and a delete name, in `If-Match`, the `ETag` the file's read gave, and a new file
comes with `If-None-Match: *`, so a change made elsewhere since the read is never lost unseen:
the page gets 412 with the file's SHA-256 now and decides. A restore is `cstudy start --restore`.
Each change runs on the worker, as a use case of the attempt in progress, waiting at most the
server's lock deadline for the project's lock.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import cast

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.active_attempt import attempt_in_progress
from coding_study.application.attempt_files import AttemptFileChanges, SavedFile
from coding_study.application.environment import Environment
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.web.api_attempts import ATTEMPT, read_file
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.errors import ApiError, ErrorCode, entity_tag
from coding_study.entrypoints.web.responses import JsonResponse, json_body

FILE = f"{ATTEMPT}/files/{{path:path}}"
ANY_FILE = "*"
SAVED = 200
CREATED = 201
DELETED = 204
NEEDS_PRECONDITION = (
    "a save needs If-Match with the ETag the file was read with, and a new file If-None-Match: *"
)
NEEDS_IF_MATCH = "a move or a delete needs If-Match with the ETag the file was read with"

type Endpoint = Callable[[Request], Awaitable[Response]]


async def put_file(request: Request) -> Response:
    """`If-Match` saves over the file while it still has that `ETag`; `If-None-Match: *` creates
    it; neither gets 428."""
    path: str = request.path_params["path"]
    if_match = request.headers.get("if-match")
    creates = request.headers.get("if-none-match", "").strip() == ANY_FILE
    if if_match is None and not creates:
        raise ApiError(ErrorCode.PRECONDITION_REQUIRED, NEEDS_PRECONDITION)
    text = _string_field(await json_body(request), "text")
    if if_match is None:
        created = await _changing(request, lambda files: files.create(path, text))
        return _saved(created, CREATED)
    expected = _unquoted(if_match)
    saved = await _changing(request, lambda files: files.save(path, text, expected))
    return _saved(saved, SAVED)


async def delete_file(request: Request) -> Response:
    """204; a starter or generated test file then shows `deleted` and can be restored."""
    path: str = request.path_params["path"]
    expected = _required_if_match(request)
    await _changing(request, lambda files: files.delete(path, expected))
    return Response(status_code=DELETED)


async def move_file(request: Request) -> Response:
    """`{"to": …}`: the file's new path and its SHA-256, which a move keeps."""
    path: str = request.path_params["path"]
    expected = _required_if_match(request)
    target = _string_field(await json_body(request), "to")
    moved = await _changing(request, lambda files: files.move(path, target, expected))
    return _saved(moved, SAVED)


async def restore_file(request: Request) -> Response:
    """`{"path": …}`: `cstudy start --restore` of a starter or generated test file."""
    path = _string_field(await json_body(request), "path")
    restored = await _changing(request, lambda files: files.restore(path))
    document = {"path": restored.path, "origin": restored.origin.value, "level": restored.level}
    return JsonResponse(document)


_FILE_METHODS: Mapping[str, Endpoint] = {
    "GET": read_file,
    "PUT": put_file,
    "DELETE": delete_file,
}


async def file_methods(request: Request) -> Response:
    """Every method of a file's path, so a method it does not take gets 405 naming them all."""
    return await _FILE_METHODS.get(request.method, read_file)(request)


def file_routes() -> Sequence[BaseRoute]:
    return [
        Route(FILE, file_methods, methods=list(_FILE_METHODS)),
        Route(f"{FILE}/move", move_file, methods=["POST"]),
        Route(f"{ATTEMPT}/restore", restore_file, methods=["POST"]),
    ]


async def _changing[Result](
    request: Request, change: Callable[[AttemptFileChanges], Result]
) -> Result:
    """`change` made to the files of the request's attempt, which must be in progress."""
    attempt_id: int = request.path_params["attempt_id"]
    deadline_s = server_state(request).settings.lock_deadline_s

    def use(environment: Environment) -> Result:
        attempt = attempt_in_progress(environment.progress, attempt_id)
        return change(AttemptFileChanges(environment, attempt, deadline_s))

    return await in_workspace(request, use)


def _saved(saved: SavedFile, status: int) -> Response:
    document = {"path": saved.path, "sha256": saved.sha256}
    return JsonResponse(document, status_code=status, headers={"etag": entity_tag(saved.sha256)})


def _required_if_match(request: Request) -> str:
    if_match = request.headers.get("if-match")
    if if_match is None:
        raise ApiError(ErrorCode.PRECONDITION_REQUIRED, NEEDS_IF_MATCH)
    return _unquoted(if_match)


def _unquoted(entity_tag_header: str) -> str:
    """The SHA-256 an `If-Match` names, without its quotes; any other value, such as a weak or
    a listed tag, then matches no file."""
    return entity_tag_header.strip().removeprefix('"').removesuffix('"')


def _string_field(document: object, name: str) -> str:
    fields = cast("dict[str, object]", document) if isinstance(document, dict) else {}
    value = fields.get(name)
    if not isinstance(value, str):
        raise UsageError(f"the request body needs {name}, a string")
    return value
