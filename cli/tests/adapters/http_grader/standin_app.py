"""A tiny app on loopback, standing in for a learner's service, and the ready stack around it: real
sockets and the real mock server, with no container."""

import json
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from coding_study.application.http_grading_ports import AppExit, StackEndpoints
from tests.mock_server_support import SAMPLE_TOKEN

ROOM_VENDOR = "room-vendor"
SECOND_VENDOR = "second-vendor"
FAST_POLL_S = 0.01


@dataclass(frozen=True)
class AppRequest:
    app: "StandInApp"
    query: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class AppAnswer:
    status: int
    document: Any = None


type Route = Callable[[AppRequest], AppAnswer | None]
"""What the app answers; None closes the connection without a word."""


class StandInApp:
    def __init__(self, routes: Mapping[tuple[str, str], Route]) -> None:
        self.exit: AppExit | None = None
        self.stopping = threading.Event()
        self.requests: list[str] = []
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(self, routes))
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        threading.Thread(
            target=self._server.serve_forever, args=(FAST_POLL_S,), daemon=True
        ).start()

    def die(self, exit_code: int, stderr_tail: str) -> None:
        """Stops listening, as a process that ended would."""
        self.exit = AppExit(exit_code, stderr_tail)
        threading.Thread(target=self.close, daemon=True).start()

    def close(self) -> None:
        self.stopping.set()
        self._server.shutdown()
        self._server.server_close()


def _handler_for(
    app: StandInApp, routes: Mapping[tuple[str, str], Route]
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _answer(self) -> None:
            target = urlsplit(self.path)
            app.requests.append(f"{self.command} {target.path}")
            length = int(self.headers.get("Content-Length", 0))
            request = AppRequest(app, dict(parse_qsl(target.query)), self.rfile.read(length))
            answer = routes[self.command, target.path](request)
            if answer is None:
                return
            body = json.dumps(answer.document).encode()
            self.send_response(answer.status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = _answer  # noqa: N815
        do_POST = _answer  # noqa: N815

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


@dataclass
class StandInStack:
    """A `GradedStack` over the stand-in and a running mock server."""

    app: StandInApp
    control_port: int
    restart_takes_s: float = 0.0
    restarts: list[str] = field(default_factory=list[str])

    @property
    def endpoints(self) -> StackEndpoints:
        return StackEndpoints(
            app_url=f"http://127.0.0.1:{self.app.port}",
            control_url=f"http://127.0.0.1:{self.control_port}",
            control_token=SAMPLE_TOKEN,
            mocks=(ROOM_VENDOR, SECOND_VENDOR),
        )

    def restart_app(self) -> None:
        self.restarts.append("app")

    def restart_app_with_fresh_data(self) -> None:
        time.sleep(self.restart_takes_s)
        self.restarts.append("fresh")

    def app_exit(self, within_ms: int) -> AppExit | None:
        return self.app.exit
