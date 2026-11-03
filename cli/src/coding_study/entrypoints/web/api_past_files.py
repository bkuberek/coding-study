"""The files of an attempt that is over, read-only (docs/specs/web-ui.md#past-attempt-files): the
listing with where the files come from, and one file. No write is routed here, and no path leaves
the folder the files are read from."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.past_attempt_files import past_attempt_files, read_past_file
from coding_study.domain.cases import JsonValue
from coding_study.entrypoints.web.api_attempts import ATTEMPT
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.documents import past_file_document, past_files_document
from coding_study.entrypoints.web.responses import JsonResponse

PAST_FILES = f"{ATTEMPT}/past-files"


async def listing(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _listing, _attempt_id(request)))


async def past_file(request: Request) -> Response:
    path: str = request.path_params["path"]
    return JsonResponse(await in_workspace(request, _file, _attempt_id(request), path))


def past_file_routes() -> list[BaseRoute]:
    return [
        Route(PAST_FILES, listing, methods=["GET"]),
        Route(f"{PAST_FILES}/{{path:path}}", past_file, methods=["GET"]),
    ]


def _attempt_id(request: Request) -> int:
    return request.path_params["attempt_id"]


def _listing(environment: Environment, attempt_id: int) -> dict[str, JsonValue]:
    return past_files_document(past_attempt_files(environment, attempt_id))


def _file(environment: Environment, attempt_id: int, path: str) -> dict[str, JsonValue]:
    return past_file_document(read_past_file(environment, attempt_id, path))
