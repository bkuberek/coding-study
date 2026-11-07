"""A server on loopback that does exactly what a test says with each connection's bytes, for what
a well-behaved HTTP server would not do."""

import re
import socket
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from tests.mock_server_support import GENEROUS_WAIT_S

_CONTENT_LENGTH = re.compile(rb"content-length: *(\d+)", re.IGNORECASE)


@dataclass
class RawServer:
    port: int
    stopping: threading.Event = field(default_factory=threading.Event)
    """Set when the test is over: a handler that holds a connection waits on it."""
    received: list[bytes] = field(default_factory=list[bytes])
    """The request of each connection whose handler called `read_request`."""

    def read_request(self, connection: socket.socket) -> bytes:
        """The head and the declared body, as they came."""
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = connection.recv(65536)
            if not chunk:
                break
            data += chunk
        head, _, body = data.partition(b"\r\n\r\n")
        declared = _CONTENT_LENGTH.search(head)
        length = int(declared[1]) if declared else 0
        while len(body) < length:
            chunk = connection.recv(65536)
            if not chunk:
                break
            body += chunk
        request = f"{head.decode()}\r\n\r\n".encode() + body
        self.received.append(request)
        return request


type Handler = Callable[[RawServer, socket.socket], None]


@contextmanager
def raw_server(handler: Handler) -> Iterator[RawServer]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        server = RawServer(listener.getsockname()[1])
        listener.settimeout(GENEROUS_WAIT_S)

        def serve(connection: socket.socket) -> None:
            with connection:
                try:
                    handler(server, connection)
                except OSError:
                    return

        def accept() -> None:
            while not server.stopping.is_set():
                try:
                    connection, _ = listener.accept()
                except OSError:
                    return
                threading.Thread(target=serve, args=(connection,), daemon=True).start()

        threading.Thread(target=accept, daemon=True).start()
        try:
            yield server
        finally:
            server.stopping.set()


def closed_port() -> int:
    """A port nothing listens on, as far as anyone can tell."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]
