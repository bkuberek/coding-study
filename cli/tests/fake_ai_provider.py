"""A stand-in for the AI providers (docs/specs/ai.md#testing): a server on the loopback that serves
each provider's own paths from a script, as `tests/fake_language_server.py` plays one for a language
server. A test or a child `cstudy` reaches it through `CSTUDY_AI_ENDPOINT`.

    with FakeAiProvider() as provider:
        provider.script(Provider.ANTHROPIC, Answer(json={"content": []}))
        environ = {"CSTUDY_AI_ENDPOINT": provider.endpoint}

`script` queues answers for one route of a provider, each served once, in order; a request's query
string does not take part in the match. A request to a path that is no provider's, or to a route
whose answers are used up, is answered 404 or 599 and kept in `unanswered`, so a test can assert
that nothing went astray. Every request is kept in `received`, its path without the query, which
is kept beside it. It imports the standard library only.
"""

import json
import socket
import threading
from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from fnmatch import fnmatchcase
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Self

from coding_study.domain.ai import Provider

UNSCRIPTED_STATUS = 599
DRIP_CHUNK_BYTES = 8


class Route(StrEnum):
    COMPLETE = "complete"
    MODELS = "models"


PATHS: Mapping[Provider, Mapping[Route, str]] = {
    Provider.ANTHROPIC: {Route.COMPLETE: "/v1/messages", Route.MODELS: "/v1/models"},
    Provider.OPENAI: {Route.COMPLETE: "/v1/responses", Route.MODELS: "/v1/models"},
    Provider.GOOGLE: {
        Route.COMPLETE: "/v1beta/models/{model}:generateContent",
        Route.MODELS: "/v1beta/models",
    },
    Provider.OPENROUTER: {
        Route.COMPLETE: "/api/v1/chat/completions",
        Route.MODELS: "/api/v1/models",
    },
}
"""Each provider's own paths; Google's names the model."""


def path_of(provider: Provider, route: Route, model_id: str = "") -> str:
    return PATHS[provider][route].format(model=model_id)


@dataclass(frozen=True, slots=True)
class Answer:
    """What the fake sends back for one request."""

    status: int = 200
    json: Any = None
    """The body as JSON, unless `body` is set."""
    body: bytes | None = None
    """The body as it is, for what is no JSON or is too long."""
    delay_s: float = 0.0
    """Before it sends anything."""
    drip_s: float = 0.0
    """Between the pieces of its body, which it sends a few bytes at a time."""
    headers: Mapping[str, str] = field(default_factory=lambda: {})


@dataclass(frozen=True, slots=True)
class Received:
    method: str
    path: str
    headers: Mapping[str, str]
    """With lower-case names."""
    body: bytes
    query: str = ""
    """What follows the `?` of the path, which routes ignore."""

    @property
    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def route_path(self) -> str:
        """The path a script matches: `path`, which holds no query."""
        return self.path


class FakeAiProvider:
    def __init__(self, host: str = "127.0.0.1") -> None:
        self.received: list[Received] = []
        self.unanswered: list[Received] = []
        self._routes: dict[tuple[str, str], deque[Answer]] = defaultdict(deque)
        self._stop = threading.Event()
        self._server = _server(host, self)
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        self.endpoint = _url(host, self._server.server_address[1])

    def script(
        self,
        provider: Provider,
        route: Route,
        *answers: Answer,
        model_id: str = "",
    ) -> None:
        method = "POST" if route is Route.COMPLETE else "GET"
        self._routes[(method, path_of(provider, route, model_id))].extend(answers)

    def requests_to(self, provider: Provider, route: Route, model_id: str = "") -> list[Received]:
        path = path_of(provider, route, model_id)
        return [request for request in self.received if request.route_path == path]

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *_exception: object) -> None:
        self._stop.set()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

    def answer(self, request: Received) -> Answer:
        self.received.append(request)
        queue = self._routes.get((request.method, request.route_path))
        if queue:
            return queue.popleft()
        self.unanswered.append(request)
        if not _is_provider_path(request.route_path):
            return Answer(404, json={"error": {"message": f"no route {request.path}"}})
        return Answer(UNSCRIPTED_STATUS, json={"error": {"message": "no scripted answer"}})

    def pause(self, seconds: float) -> None:
        """Waits, and returns early once the fake stops."""
        self._stop.wait(seconds)


def _is_provider_path(path: str) -> bool:
    return any(
        fnmatchcase(path, template.format(model="*"))
        for paths in PATHS.values()
        for template in paths.values()
    )


def _url(host: str, port: int) -> str:
    return f"http://[{host}]:{port}" if ":" in host else f"http://{host}:{port}"


def _server(host: str, provider: FakeAiProvider) -> ThreadingHTTPServer:
    class Server(ThreadingHTTPServer):
        daemon_threads = True
        address_family = socket.AF_INET6 if ":" in host else socket.AF_INET

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._serve()

        def do_POST(self) -> None:
            self._serve()

        def _serve(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            path, _, query = self.path.partition("?")
            request = Received(
                self.command,
                path,
                {name.lower(): value for name, value in self.headers.items()},
                self.rfile.read(length),
                query,
            )
            answer = provider.answer(request)
            provider.pause(answer.delay_s)
            body = answer.body if answer.body is not None else json.dumps(answer.json).encode()
            try:
                self._send(answer, body)
            except (BrokenPipeError, ConnectionResetError):
                return

        def _send(self, answer: Answer, body: bytes) -> None:
            self.send_response(answer.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for name, value in answer.headers.items():
                self.send_header(name, value)
            self.end_headers()
            if not answer.drip_s:
                self.wfile.write(body)
                return
            for start in range(0, len(body), DRIP_CHUNK_BYTES):
                self.wfile.write(body[start : start + DRIP_CHUNK_BYTES])
                self.wfile.flush()
                provider.pause(answer.drip_s)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Server((host, 0), Handler)
