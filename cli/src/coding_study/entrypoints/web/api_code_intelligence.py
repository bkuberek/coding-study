"""`GET /api/v1/code-intelligence/languages`: the state of each language's server
(docs/specs/web-ui.md#code-intelligence)."""

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.code_intelligence import LanguageServerState, language_server_states
from coding_study.application.environment import Environment
from coding_study.entrypoints.web.context import in_workspace
from coding_study.entrypoints.web.responses import JsonResponse


async def languages(request: Request) -> Response:
    states = await in_workspace(request, _states)
    return JsonResponse({"languages": [_entry(state) for state in states]})


def code_intelligence_routes() -> list[BaseRoute]:
    return [Route("/api/v1/code-intelligence/languages", languages, methods=["GET"])]


def _states(environment: Environment) -> tuple[LanguageServerState, ...]:
    return language_server_states(environment.language_servers)


def _entry(state: LanguageServerState) -> dict[str, object]:
    return {
        "language": state.language.value,
        "server": state.server,
        "version": state.version,
        "state": state.status.value,
        "detail": state.detail,
        "idle_s": state.idle_s,
    }
