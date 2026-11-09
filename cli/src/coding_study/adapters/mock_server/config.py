"""The rendered configuration of a stack's mock servers, read once at start.

cstudy validates each mock server's YAML against schemas/mock.schema.json and renders them into this
one JSON document. The program has no JSON Schema library, so it checks what would otherwise fail
during a request, and names the place in the document when it refuses one.
"""

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

MOCK_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
PATH = re.compile(r"(/([^/{}?#\s]*|\{[A-Za-z_][A-Za-z0-9_]*\}))+")
HEADER_NAME = re.compile(r"[A-Za-z0-9-]+")
UPSTREAM = re.compile(r"http://[a-z0-9]([a-z0-9.-]*[a-z0-9])?(:[0-9]{1,5})?")
"""An origin on the stack's network: a scheme, a name and a port, with no path."""
HTTP_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
LOWEST_STATUS = 200
HIGHEST_STATUS = 599
HEADER_ENCODING = "latin-1"
"""What `http.server` encodes a header with; another character would fail during a request."""

STACK_FIELDS = frozenset({"control_token", "mocks"})
MOCK_FIELDS = frozenset({"upstream", "routes", "scenarios"})
ROUTE_FIELDS = frozenset({"id", "method", "path", "query", "response"})
RESPONSE_FIELDS = frozenset({"status", "headers", "body", "body_file", "delay_ms"})
ENTRY_FIELDS = RESPONSE_FIELDS | {"jwt"}
"""A scenario entry's fields: a route's response, plus a JWT to tamper with."""
SCENARIO_FIELDS = ENTRY_FIELDS | {"visible", "route", "sequence"}
JWT_FIELDS = frozenset({"field", "tamper"})


class ConfigError(Exception):
    """The configuration cannot be served; the message names the place."""


@dataclass(frozen=True)
class Body:
    content: bytes
    content_type: str | None = None
    """What a body built from a mapping or list is sent as, unless the headers say otherwise."""


class TamperKind(StrEnum):
    """How a scenario spoils a JWT in an answer. Neither signs anything: the mock server holds no
    key."""

    ALG_NONE = "alg_none"
    """The header becomes `{"alg":"none"}` and the signature is dropped; the payload stays."""
    BAD_SIGNATURE = "bad_signature"
    """One character of the signature changes; the header and the payload stay."""


@dataclass(frozen=True)
class JwtTamper:
    field: tuple[str, ...]
    """The dotted path, split, of the JSON field of the answer that holds the token."""
    kind: TamperKind


@dataclass(frozen=True)
class ResponseFields:
    """A route's response or a scenario's override; `None` is a field left out."""

    status: int | None = None
    headers: Mapping[str, str] | None = None
    body: Body | None = None
    delay_ms: int | None = None
    jwt: JwtTamper | None = None
    """A scenario's only: the JWT of the answer it spoils."""


@dataclass(frozen=True)
class Route:
    id: str
    method: str
    path: str
    query: Mapping[str, str]
    response: ResponseFields | None
    """None passes the request through to the mock server's upstream."""


@dataclass(frozen=True)
class Scenario:
    name: str
    route_id: str | None
    entries: tuple[ResponseFields, ...]
    """One per request, in order; a plain scenario has one."""


@dataclass(frozen=True)
class MockDefinition:
    name: str
    routes: tuple[Route, ...]
    scenarios: Mapping[str, Scenario]
    upstream: str | None = None
    """`http://<name>:<port>`, which a route without a response, and a request no route matches,
    pass through to."""


@dataclass(frozen=True)
class StackConfig:
    control_token: str
    mocks: tuple[MockDefinition, ...]


def load_stack_config(path: Path) -> StackConfig:
    try:
        document: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read {path}: {error.strerror}") from error
    except ValueError as error:
        raise ConfigError(f"{path} is not JSON: {error}") from error
    return _Reader(path.parent).stack(document)


class _Fields:
    """A mapping in the document, which refuses fields it does not know and names their place."""

    def __init__(self, raw: object, allowed: frozenset[str], where: str) -> None:
        self._values = _mapping(raw, where)
        self.where = where
        unknown = self._values.keys() - allowed
        if unknown:
            raise ConfigError(f"{where}: unknown fields {sorted(unknown)}")

    def has(self, name: str) -> bool:
        return name in self._values

    def among(self, names: frozenset[str]) -> dict[str, object]:
        return {name: value for name, value in self._values.items() if name in names}

    def optional[T](self, name: str, read: Callable[[object, str], T]) -> T | None:
        return self.required(name, read) if self.has(name) else None

    def required[T](self, name: str, read: Callable[[object, str], T]) -> T:
        place = f"{self.where}.{name}"
        if not self.has(name):
            raise ConfigError(f"{place}: required")
        return read(self._values[name], place)


class _Reader:
    """Reads the document; `body_file` paths are relative to `folder`."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder.resolve()

    def stack(self, raw: object) -> StackConfig:
        fields = _Fields(raw, STACK_FIELDS, "config")
        token = fields.required("control_token", _string)
        if not token:
            raise ConfigError("config.control_token: must not be empty")
        mocks = fields.required("mocks", _mapping)
        if not mocks:
            raise ConfigError("config.mocks: expected at least one mock server")
        return StackConfig(token, tuple(self._mock(name, mocks[name]) for name in mocks))

    def _mock(self, name: str, raw: object) -> MockDefinition:
        where = f"config.mocks.{name}"
        if not MOCK_NAME.fullmatch(name):
            raise ConfigError(f"{where}: a name is lowercase letters, digits and hyphens")
        fields = _Fields(raw, MOCK_FIELDS, where)
        upstream = fields.optional("upstream", _upstream)
        routes = fields.required("routes", self._routes)
        scenarios = fields.optional("scenarios", self._scenarios) or {}
        _refuse_unknown_routes(scenarios, routes, where)
        if upstream is None:
            _refuse_routes_without_a_response(routes, where)
        return MockDefinition(name, routes, scenarios, upstream)

    def _routes(self, raw: object, where: str) -> tuple[Route, ...]:
        items = _list(raw, where)
        if not items:
            raise ConfigError(f"{where}: expected at least one route")
        routes = tuple(self._route(item, f"{where}[{i}]") for i, item in enumerate(items))
        _refuse_duplicate_ids(routes, where)
        return routes

    def _route(self, raw: object, where: str) -> Route:
        fields = _Fields(raw, ROUTE_FIELDS, where)
        response = fields.optional("response", self._response_fields)
        if response is not None and response.status is None:
            raise ConfigError(f"{where}.response.status: required")
        return Route(
            id=fields.required("id", _string),
            method=fields.required("method", _method),
            path=fields.required("path", _path),
            query=fields.optional("query", _string_mapping) or {},
            response=response,
        )

    def _scenarios(self, raw: object, where: str) -> dict[str, Scenario]:
        scenarios = _mapping(raw, where)
        return {
            name: self._scenario(name, scenarios[name], f"{where}.{name}") for name in scenarios
        }

    def _scenario(self, name: str, raw: object, where: str) -> Scenario:
        fields = _Fields(raw, SCENARIO_FIELDS, where)
        return Scenario(name, fields.optional("route", _string), self._scenario_entries(fields))

    def _scenario_entries(self, fields: _Fields) -> tuple[ResponseFields, ...]:
        overrides = fields.among(ENTRY_FIELDS)
        if not fields.has("sequence"):
            return (self._entry(overrides, fields.where),)
        if overrides:
            raise ConfigError(f"{fields.where}.sequence: cannot stand next to {sorted(overrides)}")
        return fields.required("sequence", self._sequence)

    def _sequence(self, raw: object, where: str) -> tuple[ResponseFields, ...]:
        items = _list(raw, where)
        if not items:
            raise ConfigError(f"{where}: expected at least one entry")
        return tuple(self._entry(item, f"{where}[{i}]") for i, item in enumerate(items))

    def _entry(self, raw: object, where: str) -> ResponseFields:
        entry = self._fields_of(_Fields(raw, ENTRY_FIELDS, where))
        if entry == ResponseFields():
            raise ConfigError(f"{where}: overrides nothing")
        return entry

    def _response_fields(self, raw: object, where: str) -> ResponseFields:
        return self._fields_of(_Fields(raw, RESPONSE_FIELDS, where))

    def _fields_of(self, fields: _Fields) -> ResponseFields:
        return ResponseFields(
            status=fields.optional("status", _status),
            headers=fields.optional("headers", _headers),
            body=self._body(fields),
            delay_ms=fields.optional("delay_ms", _delay),
            jwt=fields.optional("jwt", _jwt),
        )

    def _body(self, fields: _Fields) -> Body | None:
        if fields.has("body") and fields.has("body_file"):
            raise ConfigError(f"{fields.where}.body_file: cannot stand next to body")
        return fields.optional("body", _inline_body) or fields.optional(
            "body_file", self._body_file
        )

    def _body_file(self, raw: object, where: str) -> Body:
        name = _string(raw, where)
        path = (self._folder / name).resolve()
        if not path.is_relative_to(self._folder):
            raise ConfigError(f"{where}: {name} is outside the configuration's folder")
        try:
            return Body(path.read_bytes())
        except OSError as error:
            raise ConfigError(f"{where}: cannot read {name}: {error.strerror}") from error


def _refuse_duplicate_ids(routes: tuple[Route, ...], where: str) -> None:
    seen: set[str] = set()
    for route in routes:
        if route.id in seen:
            raise ConfigError(f"{where}: more than one route has the id {route.id!r}")
        seen.add(route.id)


def _refuse_unknown_routes(
    scenarios: Mapping[str, Scenario], routes: tuple[Route, ...], where: str
) -> None:
    known = {route.id for route in routes}
    for scenario in scenarios.values():
        if scenario.route_id is not None and scenario.route_id not in known:
            raise ConfigError(
                f"{where}.scenarios.{scenario.name}.route: "
                f"no route has the id {scenario.route_id!r}"
            )


def _refuse_routes_without_a_response(routes: tuple[Route, ...], where: str) -> None:
    for index, route in enumerate(routes):
        if route.response is None:
            place = f"{where}.routes[{index}].response"
            raise ConfigError(f"{place}: required, unless the mock server has an upstream")


def _upstream(raw: object, where: str) -> str:
    upstream = _string(raw, where)
    if not UPSTREAM.fullmatch(upstream):
        raise ConfigError(f"{where}: {upstream!r} must be http://<name>:<port>, with no path")
    return upstream


def _jwt(raw: object, where: str) -> JwtTamper:
    fields = _Fields(raw, JWT_FIELDS, where)
    path = fields.required("field", _string)
    kind = fields.required("tamper", _string)
    if not path or "" in path.split("."):
        raise ConfigError(f"{where}.field: a dotted path of JSON field names, got {path!r}")
    if kind not in set(TamperKind):
        known = sorted(TamperKind)
        raise ConfigError(f"{where}.tamper: expected one of {known}, got {kind!r}")
    return JwtTamper(tuple(path.split(".")), TamperKind(kind))


def _mapping(raw: object, where: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: expected a mapping")
    return cast("dict[str, object]", raw)


def _list(raw: object, where: str) -> list[object]:
    if not isinstance(raw, list):
        raise ConfigError(f"{where}: expected a list")
    return cast("list[object]", raw)


def _string(raw: object, where: str) -> str:
    if not isinstance(raw, str):
        raise ConfigError(f"{where}: expected a string")
    return raw


def _integer(raw: object, where: str) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise ConfigError(f"{where}: expected an integer")
    return raw


def _string_mapping(raw: object, where: str) -> dict[str, str]:
    fields = _mapping(raw, where)
    return {name: _string(fields[name], f"{where}.{name}") for name in fields}


def _method(raw: object, where: str) -> str:
    method = _string(raw, where)
    if method not in HTTP_METHODS:
        raise ConfigError(f"{where}: expected one of {sorted(HTTP_METHODS)}, got {method!r}")
    return method


def _path(raw: object, where: str) -> str:
    path = _string(raw, where)
    if not PATH.fullmatch(path):
        raise ConfigError(
            f"{where}: {path!r} must start with / and hold a parameter as a whole {{segment}}"
        )
    return path


def _status(raw: object, where: str) -> int:
    status = _integer(raw, where)
    if not LOWEST_STATUS <= status <= HIGHEST_STATUS:
        raise ConfigError(f"{where}: expected {LOWEST_STATUS} to {HIGHEST_STATUS}, got {status}")
    return status


def _delay(raw: object, where: str) -> int:
    delay = _integer(raw, where)
    if delay < 0:
        raise ConfigError(f"{where}: must not be negative")
    return delay


def _headers(raw: object, where: str) -> dict[str, str]:
    headers = _string_mapping(raw, where)
    for name, value in headers.items():
        if not HEADER_NAME.fullmatch(name):
            raise ConfigError(f"{where}: {name!r} is not a header name")
        if not _sendable(value):
            raise ConfigError(
                f"{where}.{name}: holds a line break or a character HTTP cannot carry"
            )
    return headers


def _sendable(header_value: str) -> bool:
    if "\r" in header_value or "\n" in header_value:
        return False
    try:
        header_value.encode(HEADER_ENCODING)
    except UnicodeEncodeError:
        return False
    return True


def _inline_body(raw: object, where: str) -> Body:
    if isinstance(raw, str):
        return Body(raw.encode())
    if isinstance(raw, dict | list):
        compact = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        return Body(compact.encode(), "application/json")
    raise ConfigError(f"{where}: expected a mapping, a list or a string")
