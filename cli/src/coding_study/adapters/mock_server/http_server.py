"""The program's two listeners: the mocked APIs on one port, the control interface on another.

They share no handler and no route table, so nothing sent to a mocked API can reach a scenario or a
log. Each connection has its own thread, so a delay holds only its own request. HTTP/1.0 closes
every connection after its answer, so no idle client keeps a thread.
"""

import io
import socket
import threading
import time
from collections.abc import Buffer, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from email.message import Message
from functools import partial
from http.server import BaseHTTPRequestHandler
from socketserver import BaseRequestHandler, TCPServer, ThreadingMixIn
from typing import Any

from .config import StackConfig
from .control import ControlInterface, ControlRequest
from .matching import MockRequest, parse_target
from .mock_state import Exchange, MockState
from .replies import Reply, json_reply, unknown_host_reply
from .request_log import MILLISECONDS_PER_SECOND

DEFAULT_API_PORT = 8080
DEFAULT_CONTROL_PORT = 9000
DEFAULT_BIND_ADDRESS = "0.0.0.0"
DEFAULT_POLL_INTERVAL_S = 0.5
MAX_REQUEST_BODY_BYTES = 1024 * 1024
MAX_CONTROL_BODY_BYTES = 64 * 1024
MAX_DISCARDED_BODY_BYTES = 16 * 1024 * 1024
DISCARD_CHUNK_BYTES = 64 * 1024
MAX_API_CONNECTIONS = 24
"""Past this a connection waits in the listen queue: the container's limit is 32 processes, and a
thread it could not start would fail the request."""
MAX_CONTROL_CONNECTIONS = 4
LISTEN_QUEUE_SIZE = 128
SOCKET_TIMEOUT_S = 10.0
"""How long a client that stopped sending or reading can hold a thread, and how long the control
port gives a whole request."""
STATUSES_WITHOUT_A_BODY = frozenset({204, 304})
CONTENT_LENGTH = "content-length"


class _BodyRefusedError(Exception):
    def __init__(self, reply: Reply, unread_bytes: int = 0) -> None:
        super().__init__(reply.status)
        self.reply = reply
        self.unread_bytes = unread_bytes


class _JsonHandler(BaseHTTPRequestHandler):
    """Writes replies byte for byte, with no `Date` or `Server` header, since a mocked API's
    answers hold no clock; errors of `http.server` itself are JSON too."""

    protocol_version = "HTTP/1.0"
    timeout = SOCKET_TIMEOUT_S
    disable_nagle_algorithm = True

    def __getattr__(self, name: str) -> Callable[[], None]:
        """`http.server` looks up `do_<METHOD>`. Every method goes the same way, since which ones
        a mocked API answers is its config's business."""
        if name.startswith("do_"):
            return self._serve_unless_gone
        raise AttributeError(name)

    def serve(self) -> None:
        raise NotImplementedError

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        # A malformed request line can leave request_version at HTTP/0.9, which suppresses the
        # status line and headers. Every error goes out as a full HTTP/1.0 response.
        self.request_version = ""
        self.write_reply(json_reply(code, {"error": message or self.responses[code][0]}))

    def write_reply(self, reply: Reply) -> None:
        self.send_response_only(reply.status)
        for name, value in reply.headers.items():
            self.send_header(name, value)
        carries_a_body = reply.status not in STATUSES_WITHOUT_A_BODY
        if carries_a_body and not _names_a_length(reply.headers):
            self.send_header("Content-Length", str(len(reply.body)))
        self.end_headers()
        if carries_a_body and self.command != "HEAD":
            self.wfile.write(reply.body)

    def read_body(self, limit: int) -> bytes:
        """The request's body, by its `Content-Length`."""
        if self.headers.get("Transfer-Encoding"):
            error = {"error": "a request body needs a Content-Length; chunked is not supported"}
            raise _BodyRefusedError(json_reply(411, error))
        length = _declared_length(self.headers)
        if length > limit:
            error = {"error": "request body too large", "limit_bytes": limit}
            raise _BodyRefusedError(json_reply(413, error), unread_bytes=length)
        return self.rfile.read(length)

    def discard(self, unread_bytes: int) -> None:
        """Reads what a refused request still has on its way, up to a bound: closing with unread
        bytes resets the connection, which can lose the answer before the client reads it."""
        remaining = min(unread_bytes, MAX_DISCARDED_BODY_BYTES)
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, DISCARD_CHUNK_BYTES))
            if not chunk:
                return
            remaining -= len(chunk)

    def _serve_unless_gone(self) -> None:
        try:
            self.serve()
        except ConnectionError:
            self.close_connection = True


class _ApiHandler(_JsonHandler):
    def __init__(self, mocks: Mapping[str, MockState], *args: Any) -> None:
        self._mocks = mocks
        super().__init__(*args)

    def serve(self) -> None:
        host = self.headers.get("Host")
        mock = self._mocks.get(_mock_name_in(host))
        if mock is None:
            self.write_reply(unknown_host_reply(host, list(self._mocks)))
            return
        self._serve_mock(mock)

    def _serve_mock(self, mock: MockState) -> None:
        try:
            body = self.read_body(MAX_REQUEST_BODY_BYTES)
        except _BodyRefusedError as refused:
            self._answer(mock, mock.refuse(self._mock_request(b""), refused.reply))
            self.discard(refused.unread_bytes)
            return
        self._answer(mock, mock.receive(self._mock_request(body)))

    def _answer(self, mock: MockState, exchange: Exchange) -> None:
        try:
            time.sleep(exchange.reply.delay_ms / MILLISECONDS_PER_SECOND)
            self.write_reply(exchange.reply)
        finally:
            mock.finish(exchange)

    def _mock_request(self, body: bytes) -> MockRequest:
        path, query = parse_target(self.path)
        return MockRequest(self.command, path, query, _lowercase_headers(self.headers), body)


class _ReadUntil(io.RawIOBase):
    """A socket's timeout bounds one read, so a client that sends a byte now and then would keep its
    thread for as long as it likes. This limits all the reads of a request together."""

    def __init__(self, connection: socket.socket, limit_s: float) -> None:
        self._connection = connection
        self._deadline = time.monotonic() + limit_s

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Buffer, /) -> int:
        left = self._deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError
        self._connection.settimeout(left)
        return self._connection.recv_into(buffer)


class _ControlHandler(_JsonHandler):
    """The app can reach this port, which has few slots for a grader that must get one. So a request
    without the token gets no further than its head, and a whole request has a limit."""

    def __init__(self, control: ControlInterface, *args: Any) -> None:
        self._control = control
        super().__init__(*args)

    def setup(self) -> None:
        super().setup()
        self.rfile.close()
        self.rfile = io.BufferedReader(_ReadUntil(self.connection, SOCKET_TIMEOUT_S))

    def serve(self) -> None:
        authorization = self.headers.get("Authorization")
        if self._control.authorized(authorization):
            self._serve_authorized(authorization)
            return
        self.write_reply(self._answer_to(authorization, b""))
        with suppress(_BodyRefusedError):
            self.read_body(MAX_CONTROL_BODY_BYTES)

    def _serve_authorized(self, authorization: str | None) -> None:
        try:
            body = self.read_body(MAX_CONTROL_BODY_BYTES)
        except _BodyRefusedError as refused:
            self.write_reply(refused.reply)
            self.discard(refused.unread_bytes)
            return
        self.write_reply(self._answer_to(authorization, body))

    def _answer_to(self, authorization: str | None, body: bytes) -> Reply:
        return self._control.handle(ControlRequest(self.command, self.path, authorization, body))


class BoundedServer(ThreadingMixIn, TCPServer):
    """One daemon thread per connection, at most `max_connections` at once. It binds with no name
    lookup, which `http.server.HTTPServer` does and which is slow on a network without DNS."""

    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = LISTEN_QUEUE_SIZE

    def __init__(
        self,
        address: tuple[str, int],
        handler: Callable[..., BaseRequestHandler],
        max_connections: int,
    ) -> None:
        self._slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request: Any, client_address: Any) -> None:
        self._slots.acquire()
        super().process_request(request, client_address)

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


@dataclass(frozen=True)
class ListenOn:
    bind_address: str = DEFAULT_BIND_ADDRESS
    api_port: int = DEFAULT_API_PORT
    control_port: int = DEFAULT_CONTROL_PORT


class RunningServers:
    def __init__(self, api: BoundedServer, control: BoundedServer, poll_interval_s: float) -> None:
        self._servers = (api, control)
        for server in self._servers:
            threading.Thread(
                target=server.serve_forever, args=(poll_interval_s,), daemon=True
            ).start()

    @property
    def api_port(self) -> int:
        return self._servers[0].server_address[1]

    @property
    def control_port(self) -> int:
        return self._servers[1].server_address[1]

    def close(self) -> None:
        for server in self._servers:
            server.shutdown()
            server.server_close()


def start_servers(
    config: StackConfig, listen: ListenOn, poll_interval_s: float = DEFAULT_POLL_INTERVAL_S
) -> RunningServers:
    """Binds both ports before serving either, so a health check that answers means both are up."""
    mocks = {definition.name: MockState(definition) for definition in config.mocks}
    control = ControlInterface(mocks, config.control_token)
    return RunningServers(
        BoundedServer(
            (listen.bind_address, listen.api_port),
            partial(_ApiHandler, mocks),
            MAX_API_CONNECTIONS,
        ),
        BoundedServer(
            (listen.bind_address, listen.control_port),
            partial(_ControlHandler, control),
            MAX_CONTROL_CONNECTIONS,
        ),
        poll_interval_s,
    )


def _mock_name_in(host_header: str | None) -> str:
    """The name in a `Host` header: lowercase, without its port."""
    host = (host_header or "").strip().lower()
    name, colon, _port = host.rpartition(":")
    return name if colon else host


def _lowercase_headers(headers: Message) -> dict[str, str]:
    """Header names in lowercase; a repeated header's values joined, as HTTP defines."""
    lowered: dict[str, str] = {}
    for name, value in headers.items():
        key = name.lower()
        lowered[key] = f"{lowered[key]}, {value}" if key in lowered else str(value)
    return lowered


def _declared_length(headers: Message) -> int:
    declared = headers.get("Content-Length")
    if declared is None:
        return 0
    if not (declared.isascii() and declared.isdigit()):
        error = {"error": f"not a Content-Length: {declared}"}
        raise _BodyRefusedError(json_reply(400, error))
    return int(declared)


def _names_a_length(headers: Mapping[str, str]) -> bool:
    return any(name.lower() == CONTENT_LENGTH for name in headers)
