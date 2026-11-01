"""`GET /api/v1/events`: the notification stream of a tab (docs/specs/web-ui.md#notifications)."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.entrypoints.web.context import server_state
from coding_study.entrypoints.web.responses import event_stream

EVENTS = "/api/v1/events"


async def events(request: Request) -> Response:
    return event_stream(request, server_state(request).notifications.frames)


def event_routes() -> list[BaseRoute]:
    return [Route(EVENTS, events, methods=["GET"])]
