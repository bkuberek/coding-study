"""One mock server's live state: its scenario, its place in a sequence and its request log.

Every change holds the lock, so concurrent requests each take their own sequence entry. Nothing here
sleeps: a delay happens after the lock is released, in the request's own thread.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from .config import MockDefinition, ResponseFields, Route, Scenario
from .matching import MockRequest, find_route, reply_for, scenario_applies, scenario_entry
from .replies import Reply, no_route_reply
from .request_log import LogEntry, Outcome, RequestLog


class UnknownScenarioError(Exception):
    def __init__(self, name: str, known: list[str]) -> None:
        super().__init__(name)
        self.known = known


@dataclass(frozen=True)
class Exchange:
    """A request's answer, and the log entry its response time goes on."""

    reply: Reply
    entry: LogEntry | None


class MockState:
    def __init__(
        self, definition: MockDefinition, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._definition = definition
        self._lock = threading.Lock()
        self._log = RequestLog(definition.name, clock)
        self._scenario: Scenario | None = None
        self._position = 0

    def receive(self, request: MockRequest) -> Exchange:
        with self._lock:
            route = find_route(self._definition.routes, request)
            if route is None:
                reply = no_route_reply(self._definition.name, request.method, request.path)
                return self._logged(request, reply, Outcome(None, None, reply.status))
            return self._matched(request, route)

    def refuse(self, request: MockRequest, reply: Reply) -> Exchange:
        """Logs a request the program refused before matching it."""
        with self._lock:
            return self._logged(request, reply, Outcome(None, None, reply.status))

    def finish(self, exchange: Exchange) -> None:
        with self._lock:
            self._log.mark_responded(exchange.entry)

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
            reply = reply_for(route, None)
            return self._logged(request, reply, Outcome(route.id, None, reply.status))
        reply = reply_for(route, self._next_entry(scenario))
        return self._logged(request, reply, Outcome(route.id, scenario.name, reply.status))

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
