"""The control interface: set a scenario, reset, read a log. Pure of sockets.

Spec: docs/specs/service-projects.md#control-interface. Only `GET /health`, which tells nothing but
that the program is up, answers without the token.
"""

import hmac
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import cast

from .mock_state import MockState, UnknownScenarioError
from .replies import Reply, json_reply

HEALTH_PATH = "/health"
BEARER_PREFIX = "Bearer "
SCENARIO_FIELD = "scenario"
NOT_A_SCENARIO_BODY = 'expected a body of {"scenario": <a name, or null for none>}'


@dataclass(frozen=True)
class ControlRequest:
    method: str
    target: str
    authorization: str | None
    body: bytes


class ControlInterface:
    def __init__(self, mocks: Mapping[str, MockState], token: str) -> None:
        self._mocks = mocks
        self._token = token.encode()

    def handle(self, request: ControlRequest) -> Reply:
        path = request.target.partition("?")[0]
        if request.method == "GET" and path == HEALTH_PATH:
            return json_reply(200, {"status": "ok"})
        if not self._authorized(request.authorization):
            return _with_header(
                json_reply(401, {"error": "a valid bearer token is required"}),
                ("WWW-Authenticate", "Bearer"),
            )
        return self._dispatch(request, path)

    def _authorized(self, authorization: str | None) -> bool:
        if authorization is None or not authorization.startswith(BEARER_PREFIX):
            return False
        return hmac.compare_digest(authorization.removeprefix(BEARER_PREFIX).encode(), self._token)

    def _dispatch(self, request: ControlRequest, path: str) -> Reply:
        action: Callable[[], Reply]
        match path.split("/")[1:]:
            case ["reset"]:
                allowed, action = "POST", self._reset
            case ["mocks", name, "scenario"]:
                allowed, action = "PUT", lambda: self._set_scenario(name, request.body)
            case ["mocks", name, "log"]:
                allowed, action = "GET", lambda: self._read_log(name)
            case _:
                return json_reply(404, {"error": "no such control path", "path": path})
        if request.method != allowed:
            error = {"error": f"{path} answers {allowed}"}
            return _with_header(json_reply(405, error), ("Allow", allowed))
        return action()

    def _reset(self) -> Reply:
        for mock in self._mocks.values():
            mock.reset()
        return json_reply(200, {"reset": True})

    def _set_scenario(self, mock_name: str, body: bytes) -> Reply:
        mock = self._mocks.get(mock_name)
        if mock is None:
            return self._unknown_mock(mock_name)
        try:
            scenario = _scenario_named_in(body)
            mock.set_scenario(scenario)
        except ValueError:
            return json_reply(400, {"error": NOT_A_SCENARIO_BODY})
        except UnknownScenarioError as unknown:
            document = {
                "error": "unknown scenario",
                "mock": mock_name,
                "scenario": str(unknown),
                "known": unknown.known,
            }
            return json_reply(404, document)
        return json_reply(200, {"mock": mock_name, "scenario": scenario})

    def _read_log(self, mock_name: str) -> Reply:
        mock = self._mocks.get(mock_name)
        if mock is None:
            return self._unknown_mock(mock_name)
        return json_reply(200, mock.log_document())

    def _unknown_mock(self, mock_name: str) -> Reply:
        document = {"error": "unknown mock server", "mock": mock_name, "known": sorted(self._mocks)}
        return json_reply(404, document)


def _scenario_named_in(body: bytes) -> str | None:
    """The name in a `{"scenario": ...}` body; `ValueError` for any other body."""
    document: object = json.loads(body)
    if not isinstance(document, dict):
        raise ValueError(NOT_A_SCENARIO_BODY)
    fields = cast("dict[str, object]", document)
    if fields.keys() != {SCENARIO_FIELD}:
        raise ValueError(NOT_A_SCENARIO_BODY)
    name = fields[SCENARIO_FIELD]
    if name is not None and not isinstance(name, str):
        raise ValueError(NOT_A_SCENARIO_BODY)
    return name


def _with_header(reply: Reply, header: tuple[str, str]) -> Reply:
    name, value = header
    return replace(reply, headers={**reply.headers, name: value})
