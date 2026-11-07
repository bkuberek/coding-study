"""`GET` and `POST /api/v1/config`: `config.toml`, as the Settings view reads and edits it
(docs/specs/web-ui.md#session-and-preferences)."""

from collections.abc import Mapping
from typing import cast

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Route

from coding_study.application.progress_db_change import progress_db_question
from coding_study.domain.config_keys import KEY_TITLES, ConfigKeyState, ConfigView
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.web.bodies import object_body, switch
from coding_study.entrypoints.web.context import in_workspace, server_state
from coding_study.entrypoints.web.errors import ApiError, ErrorCode
from coding_study.entrypoints.web.responses import JsonResponse

CHANGES_FIELD = "changes"
PROGRESS_DB = "progress_db"


async def get_config(request: Request) -> Response:
    server = server_state(request)
    view = await server.worker.run(server.settings.config_file.read)
    return JsonResponse(config_document(view))


async def post_config(request: Request) -> Response:
    """Writes `changes`, by each key's dotted name, null removing a key. A new `progress_db` moves
    no data, so without `confirm` it changes nothing and answers the question instead."""
    server = server_state(request)
    body = await object_body(request)
    changes = _changes(body)
    if PROGRESS_DB in changes and not switch(body, "confirm"):
        question = await in_workspace(request, progress_db_question, changes[PROGRESS_DB])
        if question is not None:
            raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, question)
    file = server.settings.config_file
    changed = await server.worker.run(file.apply, changes)
    view = await server.worker.run(file.read)
    return JsonResponse({**config_document(view), "changed": list(changed)})


def config_routes() -> list[BaseRoute]:
    return [
        Route("/api/v1/config", get_config, methods=["GET"]),
        Route("/api/v1/config", post_config, methods=["POST"]),
    ]


def config_document(view: ConfigView) -> dict[str, object]:
    return {
        "path": view.location,
        "exists": view.exists,
        "writable": view.writable,
        "issues": list(view.issues),
        "keys": [_key_document(state) for state in view.keys],
    }


def _key_document(state: ConfigKeyState) -> dict[str, object]:
    key = state.key
    title = KEY_TITLES[key.name]
    return {
        "name": key.name,
        "label": title.label,
        "section": title.section,
        "kind": key.kind.value,
        "value": state.value,
        "default": key.default,
        "set": state.is_set,
        "help": key.help,
        "applies": key.applies,
        "choices": list(key.choices),
        "example": key.example,
        "reserved": key.reserved,
    }


def _changes(body: Mapping[str, object]) -> Mapping[str, object]:
    changes = body.get(CHANGES_FIELD)
    if changes is None:
        raise UsageError(f"the request needs {CHANGES_FIELD}")
    if not isinstance(changes, dict):
        raise UsageError(f"invalid {CHANGES_FIELD}: use an object of keys and values")
    return cast(Mapping[str, object], changes)
