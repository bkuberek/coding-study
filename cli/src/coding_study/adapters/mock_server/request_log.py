"""What one mock server received and answered since the last reset, bounded in memory.

Not thread-safe by itself: `MockState` holds its lock around every call.
"""

import base64
import codecs
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .matching import MockRequest

MAX_LOG_ENTRIES = 1000
MAX_LOGGED_BODY_BYTES = 64 * 1024
MAX_LOG_BYTES = 8 * 1024 * 1024
"""Of bodies, headers, paths and queries, per mock server: 1,000 full bodies or request lines would
pass the 64 MiB limit of the mock server's container, and a run resets its logs between cases, long
before this."""
MILLISECONDS_PER_SECOND = 1000

type LogEntry = dict[str, object]


@dataclass(frozen=True)
class Outcome:
    route: str | None
    scenario: str | None
    status: int | None
    """None until an upstream has answered."""


class RequestLog:
    """Keeps the first entries; past a limit it counts what it dropped and says so."""

    def __init__(self, mock_name: str, clock: Callable[[], float]) -> None:
        self._mock_name = mock_name
        self._clock = clock
        self.clear()

    def clear(self) -> None:
        self._entries: list[LogEntry] = []
        self._received = 0
        self._bytes = 0
        self._began = self._clock()

    @property
    def next_seq(self) -> int:
        """The `seq` the next request recorded gets: its number since the last reset."""
        return self._received + 1

    def record(self, request: MockRequest, outcome: Outcome) -> LogEntry | None:
        """Logs a request on arrival, so a request still being answered already counts. `None`
        when the log is full."""
        self._received += 1
        size = _size_of(request)
        if len(self._entries) >= MAX_LOG_ENTRIES or self._bytes + size > MAX_LOG_BYTES:
            return None
        self._bytes += size
        entry = {
            "seq": self._received,
            "mock": self._mock_name,
            "matched": outcome.route is not None,
            "route": outcome.route,
            "scenario": outcome.scenario,
            "method": request.method,
            "path": request.path,
            "query": _query_document(request.query),
            "headers": dict(request.headers),
            **_body_fields(request.body),
            "status": outcome.status,
            "received_ms": self._elapsed_ms(),
            "responded_ms": None,
        }
        self._entries.append(entry)
        return entry

    def mark_responded(self, entry: LogEntry | None, status: int | None = None) -> None:
        """Harmless for a dropped entry, or for one a reset has already cleared. `status` is what
        an upstream answered, known only now."""
        if entry is None:
            return
        entry["responded_ms"] = self._elapsed_ms()
        if status is not None:
            entry["status"] = status

    def document(self) -> dict[str, object]:
        dropped = self._received - len(self._entries)
        return {
            "mock": self._mock_name,
            "entries": [dict(entry) for entry in self._entries],
            "truncated": dropped > 0,
            "dropped": dropped,
        }

    def _elapsed_ms(self) -> int:
        return round((self._clock() - self._began) * MILLISECONDS_PER_SECOND)


def _query_document(query: Mapping[str, tuple[str, ...]]) -> dict[str, str | list[str]]:
    """A key's value, or a list of them when the request repeated the key."""
    return {name: values[0] if len(values) == 1 else list(values) for name, values in query.items()}


def _body_fields(body: bytes) -> dict[str, object]:
    """`body` as text; a body that is not UTF-8 goes in `body_base64`, so nothing sent is lost."""
    if not body:
        return {"body": None}
    kept = body[:MAX_LOGGED_BODY_BYTES]
    truncated = len(body) > MAX_LOGGED_BODY_BYTES
    marker: dict[str, object] = {"truncated": True} if truncated else {}
    try:
        text = codecs.getincrementaldecoder("utf-8")().decode(kept, final=not truncated)
    except UnicodeDecodeError:
        return {"body": None, "body_base64": base64.b64encode(kept).decode(), **marker}
    return {"body": text, **marker}


def _size_of(request: MockRequest) -> int:
    headers = sum(len(name) + len(value) for name, value in request.headers.items())
    query = sum(
        len(name) + sum(len(value) for value in values) for name, values in request.query.items()
    )
    return len(request.path) + query + headers + min(len(request.body), MAX_LOGGED_BODY_BYTES)
