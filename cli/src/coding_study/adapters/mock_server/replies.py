"""What the program answers, whichever port asked."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

JSON_HEADERS: Mapping[str, str] = {"Content-Type": "application/json"}


@dataclass(frozen=True)
class Reply:
    status: int
    headers: Mapping[str, str]
    body: bytes
    delay_ms: int = 0


def json_reply(status: int, document: object) -> Reply:
    return Reply(status, JSON_HEADERS, json.dumps(document).encode())


def no_route_reply(mock: str, method: str, path: str) -> Reply:
    document = {"error": "no route", "mock": mock, "method": method, "path": path}
    return json_reply(404, document)


def unknown_host_reply(host: str | None, known: Sequence[str]) -> Reply:
    document = {"error": "unknown mock server", "host": host, "known": sorted(known)}
    return json_reply(404, document)
