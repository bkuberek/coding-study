"""The hidden and visible HTTP cases of a service project
(docs/specs/service-projects.md#hidden-http-case). Language-neutral: a case names a request and
what must come back, and nothing about the app that answers."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlencode

from coding_study.domain.cases import Expected, FunctionInput
from coding_study.domain.problem import ComparatorSpec

type QueryValue = str | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    path: str
    query: Mapping[str, QueryValue] = field(default_factory=dict[str, QueryValue])
    """A key with several values is sent once per value."""
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    body: bytes | None = None
    """Exactly what goes out, so a case can send a malformed body."""

    @property
    def target(self) -> str:
        """The path and query, as a request line names them."""
        return f"{self.path}?{urlencode(self.query, doseq=True)}" if self.query else self.path


@dataclass(frozen=True, slots=True)
class HttpExpected:
    status: int
    body: Expected | None = None
    """None accepts any body; `Expected(None)` asks for a JSON null."""
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    """Each listed header must match."""


@dataclass(frozen=True, slots=True)
class LogAssertion:
    """What the request log of a mock server must show when the case's answer is in."""

    mock: str
    route: str | None = None
    """None covers every request the mock server logged, matched or not."""
    count: int | None = None
    min_count: int | None = None
    max_count: int | None = None
    min_gap_ms: int | None = None
    """From each response to the next request (docs/specs/service-projects.md#hidden-http-case)."""


@dataclass(frozen=True, slots=True)
class HttpCaseInput(FunctionInput):
    """What an HTTP case does. It is a `FunctionInput` whose `arguments` hold the request as
    tests.json wrote it, with the scenarios it set, so that every report and event that shows a
    case's input shows this one with no code of its own."""

    request: HttpRequest
    expected: HttpExpected
    mocks: Mapping[str, str] = field(default_factory=dict[str, str])
    """The scenario per mock server; one left out has none."""
    before: tuple[HttpRequest, ...] = ()
    """Sent first, for a case that needs state; each must answer 2xx."""
    comparator: ComparatorSpec | None = None
    """None uses the problem's."""
    log: tuple[LogAssertion, ...] = ()
    fresh: bool = False
    """Restart the app and reset its data first."""
