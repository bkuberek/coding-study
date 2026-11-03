"""A WebSocket client for the slow tests of a real `cstudy serve` (docs/specs/web-ui.md#sessions):
the handshake of a page, with the headers a test chooses, and the messages and the close that
follow. It speaks through wsproto, the library the server runs on."""

import socket
from collections.abc import Iterator, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from types import TracebackType
from typing import Self

from wsproto import ConnectionType, WSConnection
from wsproto.events import (
    AcceptConnection,
    BytesMessage,
    CloseConnection,
    Event,
    Ping,
    RejectConnection,
    RejectData,
    Request,
    TextMessage,
)
from wsproto.extensions import Extension

WAIT_S = 30.0
READ_BYTES = 65536


class RefusedError(Exception):
    """The server answered the handshake with a response in place of the upgrade."""

    def __init__(self, status_code: int, headers: Mapping[str, str], body: bytes) -> None:
        super().__init__(f"the handshake was refused with {status_code}")
        self.status_code = status_code
        self.headers = headers
        self.body = body


@dataclass(frozen=True)
class Closed:
    """The server's close frame; `code` 1006 and no reason when the connection just ended."""

    code: int
    reason: str


class WebSocketClient:
    """`with WebSocketClient(...) as socket`: the handshake is done on entering."""

    def __init__(
        self,
        address: tuple[str, int],
        path: str,
        headers: Mapping[str, str],
        host: str | None = None,
        extensions: Sequence[Extension] = (),
    ) -> None:
        self._socket = socket.create_connection(address, timeout=WAIT_S)
        self._connection = WSConnection(ConnectionType.CLIENT)
        self._ended = False
        self.extensions: list[str] = []
        """What the server accepted of the extensions offered."""
        extra = [(name.lower().encode(), value.encode()) for name, value in headers.items()]
        request = Request(
            host=host or f"{address[0]}:{address[1]}",
            target=path,
            extra_headers=extra,
            extensions=list(extensions),
        )
        self._socket.sendall(self._connection.send(request))
        self._finish_handshake()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _type: type[BaseException] | None,
        _error: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.drop()

    def send_text(self, text: str) -> None:
        self._socket.sendall(self._connection.send(TextMessage(data=text)))

    def send_bytes(self, data: bytes) -> None:
        self._socket.sendall(self._connection.send(BytesMessage(data=data)))

    def receive(self) -> str | bytes | Closed:
        """The next message: text, bytes, or the close that ended the connection."""
        text, data = "", b""
        while True:
            for event in self._events():
                if isinstance(event, TextMessage):
                    text += event.data
                    if event.message_finished:
                        return text
                elif isinstance(event, BytesMessage):
                    data += event.data
                    if event.message_finished:
                        return data
                elif isinstance(event, Ping):
                    self._socket.sendall(self._connection.send(event.response()))
                elif isinstance(event, CloseConnection):
                    self._answer_close(event)
                    return Closed(event.code, event.reason or "")
            if self._ended:
                return Closed(1006, "")

    def close(self, code: int = 1000) -> None:
        """The close handshake the page starts."""
        self._socket.sendall(self._connection.send(CloseConnection(code=code)))

    def drop(self) -> None:
        """The connection ends without a close frame, as a tab that is gone leaves it."""
        self._socket.close()

    def _events(self) -> Iterator[Event]:
        try:
            data = self._socket.recv(READ_BYTES)
        except (ConnectionError, TimeoutError):
            data = b""
        if not data:
            self._ended = True
            return
        self._connection.receive_data(data)
        yield from self._connection.events()

    def _finish_handshake(self) -> None:
        refusal: RejectConnection | None = None
        body = b""
        while True:
            for event in self._events():
                if isinstance(event, AcceptConnection):
                    self.extensions = [extension.name for extension in event.extensions]
                    return
                if isinstance(event, RejectConnection):
                    refusal = event
                elif isinstance(event, RejectData):
                    body += event.data
                    if event.body_finished and refusal is not None:
                        raise _refused(refusal, body)
            if self._ended:
                raise ConnectionError("the server ended the connection during the handshake")

    def _answer_close(self, event: CloseConnection) -> None:
        with suppress(OSError, ValueError):
            self._socket.sendall(self._connection.send(event.response()))


def _refused(refusal: RejectConnection, body: bytes) -> RefusedError:
    headers = {name.decode().lower(): value.decode() for name, value in refusal.headers}
    return RefusedError(refusal.status_code, headers, body)
