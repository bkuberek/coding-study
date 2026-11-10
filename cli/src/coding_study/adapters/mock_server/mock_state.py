"""One mock server's live state: its scenario, its place in a sequence and its request log.

Every change holds the lock, so concurrent requests each take their own sequence entry. Nothing here
sleeps: a delay happens after the lock is released, in the request's own thread.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from .config import JwtTamper, MockDefinition, ResponseFields, Route, Scenario
from .matching import (
    MockRequest,
    find_route,
    passes_through,
    reply_for,
    scenario_applies,
    scenario_entry,
)
from .replies import Reply, no_route_reply
from .request_log import LogEntry, Outcome, RequestLog
from .templates import RequestValues


class UnknownScenarioError(Exception):
    def __init__(self, name: str, known: list[str]) -> None:
        super().__init__(name)
        self.known = known


@dataclass(frozen=True)
class PassThrough:
    """A request the upstream answers, outside the lock, since it takes a network round trip."""

    upstream: str
    overrides: ResponseFields | None
    """The fields a scenario gives in place of the upstream's."""


@dataclass(frozen=True)
class Exchange:
    """A request's answer, and the log entry its response time goes on."""

    reply: Reply
    """The answer; for a pass-through, only its delay counts."""
    entry: LogEntry | None
    pass_through: PassThrough | None = None
    jwt: JwtTamper | None = None
    """The JWT of the answer that a scenario spoils on its way out."""


PASSED = Reply(0, {}, b"")
"""The reply of a request no route matches that passes through: the upstream gives all of it."""


@dataclass(frozen=True)
class _Applied:
    """The scenario that applies to a request, with the entry it answers with; none by default."""

    scenario: str | None = None
    entry: ResponseFields | None = None


class MockState:
    def __init__(
        self, definition: MockDefinition, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._definition = definition
        self._lock = threading.Lock()
        self._log = RequestLog(definition.name, clock)
        self._scenario: Scenario | None = None
        self._position = 0

    @property
    def name(self) -> str:
        return self._definition.name

    def receive(self, request: MockRequest) -> Exchange:
        with self._lock:
            route = find_route(self._definition.routes, request)
            if route is not None:
                return self._matched(request, route)
            upstream = self._definition.upstream
            if upstream is not None:
                entry = self._log.record(request, Outcome(None, None, None))
                return Exchange(PASSED, entry, PassThrough(upstream, None))
            reply = no_route_reply(self._definition.name, request.method, request.path)
            return self._logged(request, reply, Outcome(None, None, reply.status))

    def refuse(self, request: MockRequest, reply: Reply) -> Exchange:
        """Logs a request the program refused before matching it."""
        with self._lock:
            return self._logged(request, reply, Outcome(None, None, reply.status))

    def finish(self, exchange: Exchange, status: int | None = None) -> None:
        """`status` is what went out, for a pass-through whose upstream has just answered."""
        with self._lock:
            self._log.mark_responded(exchange.entry, status)

    def set_scenario(self, name: str | None) -> None:
        """Sets a scenario or, with `None`, none. Its sequence starts over either way."""
        with self._lock:
            self._scenario = self._named_scenario(name)
            self._position = 0

    def reset(self) -> None:
        """Clears the log and the sequence, and sets no scenario."""
        with self._lock:
            self._scenario = None
            self._position = 0
            self._log.clear()

    def log_document(self) -> dict[str, object]:
        with self._lock:
            return self._log.document()

    def _matched(self, request: MockRequest, route: Route) -> Exchange:
        scenario = self._scenario
        if scenario is None or not scenario_applies(scenario, route):
            return self._answered(request, route, _Applied())
        return self._answered(request, route, _Applied(scenario.name, self._next_entry(scenario)))

    def _answered(self, request: MockRequest, route: Route, applied: "_Applied") -> Exchange:
        entry = applied.entry
        reply = reply_for(route, entry, RequestValues(request, self._log.next_seq))
        jwt = entry.jwt if entry is not None else None
        upstream = self._definition.upstream
        if upstream is None or not passes_through(route, entry):
            outcome = Outcome(route.id, applied.scenario, reply.status)
            return Exchange(reply, self._log.record(request, outcome), None, jwt)
        logged = self._log.record(request, Outcome(route.id, applied.scenario, None))
        return Exchange(reply, logged, PassThrough(upstream, entry), jwt)

    def _next_entry(self, scenario: Scenario) -> ResponseFields:
        entry = scenario_entry(scenario, self._position)
        self._position += 1
        return entry

    def _logged(self, request: MockRequest, reply: Reply, outcome: Outcome) -> Exchange:
        return Exchange(reply, self._log.record(request, outcome))

    def _named_scenario(self, name: str | None) -> Scenario | None:
        if name is None:
            return None
        scenario = self._definition.scenarios.get(name)
        if scenario is None:
            raise UnknownScenarioError(name, sorted(self._definition.scenarios))
        return scenario
