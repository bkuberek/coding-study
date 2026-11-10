"""A tiny app on loopback, standing in for a learner's service, and the ready stack around it: real
sockets and the real mock server, with no container."""

import json
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from coding_study.application.http_grading_ports import AppExit, StackEndpoints
from coding_study.domain.sandbox import ServiceChange
from tests.mock_server_support import SAMPLE_TOKEN

ROOM_VENDOR = "room-vendor"
APP_ORIGIN = "http://app:8000"
SECOND_VENDOR = "second-vendor"
FAST_POLL_S = 0.01


@dataclass(frozen=True)
class AppRequest:
    app: "StandInApp"
    query: Mapping[str, str]
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    """By lowercase name."""


@dataclass(frozen=True)
class AppAnswer:
    status: int
    document: Any = None
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    stream: Iterable[bytes] | None = None
    """Sent piece by piece as server-sent events, in place of `document`, with no length: closing
    the connection ends it."""


type Route = Callable[[AppRequest], AppAnswer | None]
"""What the app answers; None closes the connection without a word."""


class StandInApp:
    def __init__(self, routes: Mapping[tuple[str, str], Route]) -> None:
        self.exit: AppExit | None = None
        self.stopping = threading.Event()
        self.requests: list[str] = []
        self.printed: list[tuple[float, str]] = []
        """Each line the app printed, with the wall clock it printed it at, as an engine stamps
        a container's output."""
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(self, routes))
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        threading.Thread(
            target=self._server.serve_forever, args=(FAST_POLL_S,), daemon=True
        ).start()

    def print_line(self, line: str) -> None:
        self.printed.append((time.time(), line))

    def output_since(self, since_s: float) -> str:
        return "".join(f"{line}\n" for at, line in self.printed if at >= since_s)

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
            headers = {name.lower(): value for name, value in self.headers.items()}
            body = self.rfile.read(length)
            request = AppRequest(app, dict(parse_qsl(target.query)), body, headers)
            answer = routes[self.command, target.path](request)
            if answer is None:
                return
            if answer.stream is not None:
                self._stream(answer.status, answer.stream)
                return
            body = json.dumps(answer.document).encode()
            self.send_response(answer.status)
            for name, value in answer.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _stream(self, status: int, pieces: Iterable[bytes]) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for piece in pieces:
                self.wfile.write(piece)

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
    mocks: tuple[str, ...] = (ROOM_VENDOR, SECOND_VENDOR)
    origins: Mapping[str, str] = field(default_factory=dict[str, str])
    """What P10's forwarder would publish: each origin a case names, by its name in the stack."""

    @property
    def endpoints(self) -> StackEndpoints:
        return StackEndpoints(
            app_url=f"http://127.0.0.1:{self.app.port}",
            control_url=f"http://127.0.0.1:{self.control_port}",
            control_token=SAMPLE_TOKEN,
            mocks=self.mocks,
            app_origin=APP_ORIGIN,
            origins=self.origins,
        )

    def restart_app(self) -> None:
        self.restarts.append("app")

    def restart_app_with_fresh_data(self) -> None:
        time.sleep(self.restart_takes_s)
        self.restarts.append("fresh")

    def change_service(self, change: ServiceChange) -> None:
        self.restarts.append(f"{change.action} {change.service}")

    def app_exit(self, within_ms: int) -> AppExit | None:
        return self.app.exit

    def app_output(self, since_s: float) -> str:
        return self.app.output_since(since_s)
