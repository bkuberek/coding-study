from collections import deque

NOT_FOUND = "404"
TOO_MANY_REQUESTS = "429"
UNAVAILABLE = "503"
CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"


def _segments(path: str) -> list[str]:
    return [segment for segment in path.split("/") if segment]


class _RouteNode:
    """One trie level: literal children, one shared parameter child, and the routes ending here."""

    def __init__(self) -> None:
        self.literals: dict[str, _RouteNode] = {}
        self.parameter: _RouteNode | None = None
        self.upstream: str | None = None  # a pattern ending exactly here
        self.wildcard: str | None = None  # a pattern ending here with `*`

    def child(self, segment: str) -> "_RouteNode":
        if segment.startswith(":"):
            self.parameter = self.parameter or _RouteNode()
            return self.parameter
        return self.literals.setdefault(segment, _RouteNode())

    def match(self, segments: list[str], index: int) -> str | None:
        """The most specific upstream: literal before parameter before wildcard, left to right."""
        if index == len(segments):
            return self.upstream
        literal = self.literals.get(segments[index])
        found = literal.match(segments, index + 1) if literal else None
        if found is None and self.parameter is not None:
            found = self.parameter.match(segments, index + 1)
        return found if found is not None else self.wildcard


class _RouteTable:
    def __init__(self) -> None:
        self._roots: dict[str, _RouteNode] = {}

    def add(self, method: str, pattern: str, upstream: str) -> bool:
        node, wildcard = self._end(method, pattern)
        if (node.wildcard if wildcard else node.upstream) is not None:
            return False
        if wildcard:
            node.wildcard = upstream
        else:
            node.upstream = upstream
        return True

    def remove(self, method: str, pattern: str) -> bool:
        node, wildcard = self._end(method, pattern)
        if wildcard:
            found, node.wildcard = node.wildcard, None
        else:
            found, node.upstream = node.upstream, None
        return found is not None

    def match(self, method: str, path: str) -> str | None:
        root = self._roots.get(method)
        return root.match(_segments(path), 0) if root else None

    def _end(self, method: str, pattern: str) -> tuple[_RouteNode, bool]:
        """The node where `pattern` ends, and whether it ends with the wildcard."""
        segments = _segments(pattern)
        wildcard = bool(segments) and segments[-1] == "*"
        node = self._roots.setdefault(method, _RouteNode())
        for segment in segments[:-1] if wildcard else segments:
            node = node.child(segment)
        return node, wildcard


class _FixedWindow:
    def __init__(self, limit: int, window: int) -> None:
        self._limit, self._window = limit, window
        self._current, self._used = -1, 0

    def allows(self, now: int) -> bool:
        return now // self._window != self._current or self._used < self._limit

    def record(self, now: int) -> None:
        if now // self._window != self._current:
            self._current, self._used = now // self._window, 0
        self._used += 1


class _SlidingWindow:
    def __init__(self, limit: int, window: int) -> None:
        self._limit, self._window = limit, window
        self._accepted: deque[int] = deque()

    def allows(self, now: int) -> bool:
        while self._accepted and self._accepted[0] <= now - self._window:
            self._accepted.popleft()
        return len(self._accepted) < self._limit

    def record(self, now: int) -> None:
        self._accepted.append(now)


class _Client:
    def __init__(self) -> None:
        self.limiter: _FixedWindow | _SlidingWindow | None = None
        self.quota: int | None = None  # requests left, when a quota is set

    def allows(self, now: int) -> bool:
        within_rate = self.limiter is None or self.limiter.allows(now)
        return within_rate and (self.quota is None or self.quota > 0)

    def record(self, now: int) -> None:
        if self.limiter is not None:
            self.limiter.record(now)
        if self.quota is not None:
            self.quota -= 1


class _CircuitBreaker:
    def __init__(self, threshold: int, cooldown: int) -> None:
        self._threshold, self._cooldown = threshold, cooldown
        self._failures = 0
        self._opened_at: int | None = None
        self._trial_in_flight = False

    def state(self, now: int) -> str:
        if self._opened_at is None:
            return CLOSED
        return HALF_OPEN if now >= self._opened_at + self._cooldown else OPEN

    def allows(self, now: int) -> bool:
        state = self.state(now)
        return state == CLOSED or (state == HALF_OPEN and not self._trial_in_flight)

    def on_dispatch(self, now: int) -> None:
        if self.state(now) == HALF_OPEN:
            self._trial_in_flight = True

    def record(self, now: int, success: bool) -> str:
        state = self.state(now)
        if state == HALF_OPEN:
            self._trial_in_flight = False
            self._opened_at = None if success else now
        elif state == CLOSED:
            self._failures = 0 if success else self._failures + 1
            if self._failures >= self._threshold:
                self._failures, self._opened_at = 0, now
        return self.state(now)


class ApiGateway:
    def __init__(self) -> None:
        self._routes = _RouteTable()
        self._clients: dict[str, _Client] = {}
        self._breakers: dict[str, _CircuitBreaker] = {}

    # Level 1
    def add_route(self, timestamp: int, method: str, pattern: str, upstream: str) -> bool:
        return self._routes.add(method, pattern, upstream)

    def remove_route(self, timestamp: int, method: str, pattern: str) -> bool:
        return self._routes.remove(method, pattern)

    def route(self, timestamp: int, client_id: str, method: str, path: str) -> str:
        upstream = self._routes.match(method, path)
        if upstream is None:
            return NOT_FOUND
        breaker = self._breakers.get(upstream)
        if breaker is not None and not breaker.allows(timestamp):
            return UNAVAILABLE
        client = self._clients.get(client_id)
        if client is not None and not client.allows(timestamp):
            return TOO_MANY_REQUESTS
        if client is not None:
            client.record(timestamp)
        if breaker is not None:
            breaker.on_dispatch(timestamp)
        return upstream

    # Level 2
    def set_client_limit(self, timestamp: int, client_id: str, limit: int, window_ms: int) -> None:
        self._client(client_id).limiter = _FixedWindow(limit, window_ms)

    # Level 3
    def set_client_sliding_limit(self, timestamp: int, client_id: str, limit: int, window_ms: int) -> None:
        self._client(client_id).limiter = _SlidingWindow(limit, window_ms)

    def set_client_quota(self, timestamp: int, client_id: str, quota: int) -> None:
        self._client(client_id).quota = quota

    def remaining_quota(self, timestamp: int, client_id: str) -> int:
        client = self._clients.get(client_id)
        return -1 if client is None or client.quota is None else client.quota

    # Level 4
    def set_breaker(self, timestamp: int, upstream: str, failure_threshold: int, cooldown_ms: int) -> None:
        self._breakers[upstream] = _CircuitBreaker(failure_threshold, cooldown_ms)

    def report_result(self, timestamp: int, upstream: str, success: bool) -> str:
        breaker = self._breakers.get(upstream)
        return "" if breaker is None else breaker.record(timestamp, success)

    def breaker_state(self, timestamp: int, upstream: str) -> str:
        breaker = self._breakers.get(upstream)
        return "" if breaker is None else breaker.state(timestamp)

    def _client(self, client_id: str) -> _Client:
        return self._clients.setdefault(client_id, _Client())
