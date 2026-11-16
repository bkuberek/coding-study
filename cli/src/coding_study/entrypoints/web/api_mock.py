"""`POST /api/v1/mock` starts a mock interview as `cstudy mock` does; `GET /api/v1/mock` shows
the one whose timer runs, started from the page or the terminal, since a mock is nothing but its
attempts in progress (docs/specs/web-ui.md#mock-progress-and-health)."""

from collections.abc import Sequence
from dataclasses import replace

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.environment import Environment
from coding_study.application.mock_interview import (
    DEFAULT_COUNT,
    DEFAULT_MINUTES,
    MockRequest,
    current_mock,
    mock_scope,
    start_mock,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import Language, Track
from coding_study.domain.profile import PICK_DIMENSIONS, learner_profile
from coding_study.entrypoints.commands.list_problems import explicit_widening
from coding_study.entrypoints.web.bodies import (
    choice_list,
    object_body,
    optional_choice,
    optional_integer,
    optional_text,
    text_list,
)
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.documents import running_mock_document, started_mock_document
from coding_study.entrypoints.web.queries import choice
from coding_study.entrypoints.web.queries import choice_list as query_list
from coding_study.entrypoints.web.responses import JsonResponse

MOCK = "/api/v1/mock"
CREATED = 201
NOTHING_STARTED = 200
MINUTES = (1, 600)
"""The range of a start's `timer_minutes`: a mock's shared timer is that time box."""
COUNT = (1, 20)


async def running(request: Request) -> Response:
    """The mock that runs, or, with none, the scope a start with the query's values would pick
    from (`tracks`, repeatable, `language`, `domain`, `role` and `widen`, as `cstudy mock` takes
    them)."""
    query = request.query_params
    scoped = MockRequest(
        tracks=query_list(query, "tracks", Track),
        language=choice(query, "language", Language),
        labels=LabelFilter(query.get("domain"), query.get("role")),
    )
    return JsonResponse(await in_workspace(request, _running, scoped, query.getlist("widen")))


async def start(request: Request) -> Response:
    body = await object_body(request)
    minutes = optional_integer(body, "minutes", MINUTES)
    count = optional_integer(body, "count", COUNT)
    mock_request = MockRequest(
        minutes=DEFAULT_MINUTES if minutes is None else minutes,
        count=DEFAULT_COUNT if count is None else count,
        tracks=choice_list(body, "tracks", Track),
        language=optional_choice(body, "language", Language),
        labels=LabelFilter(optional_text(body, "domain"), optional_text(body, "role")),
    )
    document = await in_workspace(request, _start, mock_request, text_list(body, "widen"))
    status = CREATED if document["problems"] else NOTHING_STARTED
    return JsonResponse(document, status_code=status)


def mock_routes() -> list[BaseRoute]:
    return [
        Route(MOCK, running, methods=["GET"]),
        Route(MOCK, start, methods=["POST"]),
    ]


def _profiled(environment: Environment, request: MockRequest, widen: Sequence[str]) -> MockRequest:
    """`request` under the learner profile, as `cstudy mock` applies it: dropped in the
    dimension of each `widen` value and of each explicit filter."""
    labels = request.labels
    widening = explicit_widening(
        widen, request.language, labels.role, labels.domain, PICK_DIMENSIONS
    )
    profile = learner_profile(environment.config.profile, environment.workspace_languages)
    return replace(request, profile=profile, widening=widening)


def _running(
    environment: Environment, request: MockRequest, widen: Sequence[str]
) -> dict[str, JsonValue]:
    mock = current_mock(environment)
    if mock is not None:
        return running_mock_document(mock)
    return running_mock_document(
        None, mock_scope(environment, _profiled(environment, request, widen))
    )


def _start(
    environment: Environment, request: MockRequest, widen: Sequence[str]
) -> dict[str, JsonValue]:
    return started_mock_document(start_mock(environment, _profiled(environment, request, widen)))
