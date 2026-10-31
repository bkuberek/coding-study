"""`POST /api/v1/mock` starts a mock interview as `cstudy mock` does; `GET /api/v1/mock` shows
the one whose timer runs, started from the page or the terminal, since a mock is nothing but its
attempts in progress (docs/specs/web-ui.md#mock-progress-and-health)."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.mock_interview import (
    DEFAULT_COUNT,
    DEFAULT_MINUTES,
    MockRequest,
    current_mock,
    start_mock,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import Language, Track
from coding_study.entrypoints.web.bodies import (
    choice_list,
    object_body,
    optional_choice,
    optional_integer,
)
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.documents import running_mock_document, started_mock_document
from coding_study.entrypoints.web.responses import JsonResponse

MOCK = "/api/v1/mock"
CREATED = 201
NOTHING_STARTED = 200
MINUTES = (1, 600)
"""The range of a start's `timer_minutes`: a mock's shared timer is that time box."""
COUNT = (1, 20)


async def running(request: Request) -> Response:
    return JsonResponse(await in_workspace(request, _running))


async def start(request: Request) -> Response:
    body = await object_body(request)
    minutes = optional_integer(body, "minutes", MINUTES)
    count = optional_integer(body, "count", COUNT)
    mock_request = MockRequest(
        minutes=DEFAULT_MINUTES if minutes is None else minutes,
        count=DEFAULT_COUNT if count is None else count,
        tracks=choice_list(body, "tracks", Track),
        language=optional_choice(body, "language", Language),
    )
    document = await in_workspace(request, _start, mock_request)
    status = CREATED if document["problems"] else NOTHING_STARTED
    return JsonResponse(document, status_code=status)


def mock_routes() -> list[BaseRoute]:
    return [
        Route(MOCK, running, methods=["GET"]),
        Route(MOCK, start, methods=["POST"]),
    ]


def _running(environment: Environment) -> dict[str, JsonValue]:
    return running_mock_document(current_mock(environment))


def _start(environment: Environment, request: MockRequest) -> dict[str, JsonValue]:
    return started_mock_document(start_mock(environment, request))
