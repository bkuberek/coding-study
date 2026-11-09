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
    header_lines: tuple[tuple[str, str], ...] = ()
    """Headers sent after `headers`, each on its own line, so that an upstream's `Set-Cookie` lines
    stay apart."""

    def every_header(self) -> tuple[tuple[str, str], ...]:
        return (*self.headers.items(), *self.header_lines)


def json_reply(status: int, document: object) -> Reply:
    return Reply(status, JSON_HEADERS, json.dumps(document).encode())


def no_route_reply(mock: str, method: str, path: str) -> Reply:
    document = {"error": "no route", "mock": mock, "method": method, "path": path}
    return json_reply(404, document)


def unknown_host_reply(host: str | None, known: Sequence[str]) -> Reply:
    document = {"error": "unknown mock server", "host": host, "known": sorted(known)}
    return json_reply(404, document)
