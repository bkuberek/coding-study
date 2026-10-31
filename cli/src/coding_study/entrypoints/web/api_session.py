"""`GET /api/v1/session` and the preferences (docs/specs/web-ui.md#session-and-preferences)."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.preferences import read_preferences, save_preferences
from coding_study.domain.preferences import preferences_document
from coding_study.entrypoints.web.context import ServerSettings, server_state
from coding_study.entrypoints.web.documents import session_document
from coding_study.entrypoints.web.responses import JsonResponse, json_body


async def session(request: Request) -> Response:
    server = server_state(request)
    return JsonResponse(await server.worker.run(_session, server.settings))


async def get_preferences(request: Request) -> Response:
    server = server_state(request)
    preferences = await server.worker.run(read_preferences, server.settings.preferences)
    return JsonResponse(preferences_document(preferences))


async def put_preferences(request: Request) -> Response:
    server = server_state(request)
    document = await json_body(request)
    store = server.settings.preferences
    preferences = await server.worker.run(save_preferences, store, document)
    return JsonResponse(preferences_document(preferences))


def session_routes() -> list[BaseRoute]:
    return [
        Route("/api/v1/session", session, methods=["GET"]),
        Route("/api/v1/preferences", get_preferences, methods=["GET"]),
        Route("/api/v1/preferences", put_preferences, methods=["PUT"]),
    ]


def _session(settings: ServerSettings) -> dict[str, object]:
    return session_document(settings.load_environment(), settings.port, settings.version)
