"""`GET /api/v1/code-intelligence/languages`, the state of each language's server, for an attempt
when `attempt_id` names one, and `GET /api/v1/code-intelligence?attempt_id=N`, the WebSocket of a
session
(docs/specs/web-ui.md#code-intelligence, docs/specs/web-ui.md#sessions).

The handshake is checked in the spec's order: the security layer refuses a Host, a cookie or an
Origin it does not allow, and this module the attempt, the preference, the language and the
server; each refusal is an HTTP response in place of the upgrade. The page then has
`first_message_s` to send its CSRF token as the first message.
"""

import asyncio
import json
import os
import sys
from typing import cast

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route, WebSocketRoute
from starlette.websockets import WebSocket

from coding_study.application.code_intelligence import (
    LanguageServerState,
    SessionTarget,
    session_server_states,
    session_target,
    warm_up_target,
)
from coding_study.application.preferences import read_preferences
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.web.code_intelligence import bad_csrf
from coding_study.entrypoints.web.context import ServerState, in_workspace, server_state
from coding_study.entrypoints.web.errors import refusal
from coding_study.entrypoints.web.language_broker import LanguageBroker
from coding_study.entrypoints.web.queries import positive_integer
from coding_study.entrypoints.web.responses import JsonResponse
from coding_study.entrypoints.web.security import matches

SESSION = "/api/v1/code-intelligence"
ATTEMPT_ID = "attempt_id"


async def languages(request: Request) -> Response:
    """With `attempt_id`, the servers as that attempt's sessions judge them."""
    attempt_id = positive_integer(request.query_params, ATTEMPT_ID)
    states = await in_workspace(request, session_server_states, attempt_id)
    return JsonResponse({"languages": [_entry(state) for state in states]})


async def session(websocket: WebSocket) -> None:
    """Refuses the handshake, or upgrades it, waits for the CSRF message and relays the socket
    to a server until either ends."""
    server = server_state(websocket)
    try:
        target = await _admitted(websocket, server)
    except Exception as error:
        refused = refusal(error)
        if refused is None:
            raise
        await websocket.send_denial_response(refused)
        return
    await websocket.accept()
    if await _carries_token(websocket, server):
        watched = None if target.sidecar is not None else os.getpid()
        broker = LanguageBroker(target, server.settings.version, watched)
        await server.sessions.serve(websocket, target, broker)


async def warm_up(server: ServerState) -> None:
    """Starts the default language's server ahead of time while code intelligence is on and the
    server is installed (docs/specs/web-ui.md#warm-up). A server that does not start is no failure:
    the first session starts one, as it would have."""
    try:
        preferences = await server.worker.run(read_preferences, server.settings.preferences)
        environment = await server.worker.run(server.settings.load_environment)
        target = await server.worker.run(warm_up_target, environment, preferences)
        if target is not None:
            broker = LanguageBroker(target, server.settings.version, os.getpid())
            await server.sessions.warm(target, broker)
    except Exception as error:  # the page works without it; the reason is reported
        print(f"cstudy serve: no language server warmed up: {error}", file=sys.stderr)


def code_intelligence_routes() -> list[BaseRoute]:
    return [
        Route(f"{SESSION}/languages", languages, methods=["GET"]),
        WebSocketRoute(SESSION, session),
    ]


async def _admitted(websocket: WebSocket, server: ServerState) -> SessionTarget:
    """Raises what refuses the session: UsageError for an attempt_id that is missing or not a
    positive integer, and the errors of `session_target`."""
    attempt_id = positive_integer(websocket.query_params, ATTEMPT_ID)
    if attempt_id is None:
        raise UsageError(f"the request needs {ATTEMPT_ID}")
    preferences = await server.worker.run(read_preferences, server.settings.preferences)
    return await in_workspace(websocket, session_target, preferences, attempt_id)


async def _carries_token(websocket: WebSocket, server: ServerState) -> bool:
    """Whether the first message is the page's CSRF token, which it has `first_message_s` to
    send; the socket is closed with 1008 otherwise. A socket the page closed needs no close."""
    try:
        async with asyncio.timeout(server.sessions.timing.first_message_s):
            message = await websocket.receive()
    except TimeoutError:
        message = None
    if message is not None and message["type"] == "websocket.disconnect":
        return False
    if message is None or not _is_token(message.get("text"), server.settings.secrets.csrf):
        await bad_csrf().close(websocket)
        return False
    return True


def _is_token(text: str | None, csrf: str) -> bool:
    """`{"csrf": "<token>"}`, the token compared in constant time."""
    if text is None:
        return False
    try:
        document: object = json.loads(text)
    except (ValueError, RecursionError):
        return False
    if not isinstance(document, dict):
        return False
    token = cast(dict[str, object], document).get("csrf")
    return isinstance(token, str) and matches(token, csrf)


def _entry(state: LanguageServerState) -> dict[str, object]:
    return {
        "language": state.language.value,
        "server": state.server,
        "version": state.version,
        "state": state.status.value,
        "detail": state.detail,
        "idle_s": state.idle_s,
    }
