"""Runs the app on uvicorn, on a socket bound to the loopback address before the app exists, so
the port the system picks for `--port 0` is known to the session (docs/specs/web-ui.md#server).
"""

import errno
import signal
import socket
from collections.abc import Callable, Coroutine, Generator
from contextlib import contextmanager
from types import FrameType
from typing import Any

import uvicorn
from starlette.types import ASGIApp

from coding_study.entrypoints.web.security import LOOPBACK, MIB

STOP_SIGNALS = frozenset({signal.SIGINT, signal.SIGTERM})

WEBSOCKET_MESSAGE_LIMIT = 4 * MIB

type Stopping = Callable[[], Coroutine[Any, Any, None]]
"""What the server does first as it shuts down: stop the runs and jobs and end the
code-intelligence sessions."""


async def _nothing() -> None:
    pass


class PortInUseError(Exception):
    def __init__(self, port: int) -> None:
        super().__init__(f"port {port} on {LOOPBACK} is already in use; choose another with --port")


class Terminated(BaseException):
    """SIGTERM, raised once uvicorn has shut down, as KeyboardInterrupt is for Ctrl-C: a
    BaseException, so no `except Exception` on the way swallows it."""


def bind_loopback(port: int) -> socket.socket:
    """Raises PortInUseError; no option binds another address."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind((LOOPBACK, port))
    except OSError as error:
        listener.close()
        if error.errno == errno.EADDRINUSE:
            raise PortInUseError(port) from None
        raise
    # Listening now lets a client that reads the printed URL connect before uvicorn starts.
    listener.listen()
    return listener


@contextmanager
def stop_signals() -> Generator[None]:
    """From here on, SIGINT ends in KeyboardInterrupt and SIGTERM in Terminated, once the server
    has shut down. Until `serve_forever` hands them to uvicorn, they wait blocked: one that comes
    while the server starts stops it once it can, instead of killing the process (SIGTERM),
    being lost (SIGINT, which a background job inherits ignored) or breaking into the event
    loop's setup."""
    previous = {
        signal.SIGINT: signal.signal(signal.SIGINT, _interrupted),
        signal.SIGTERM: signal.signal(signal.SIGTERM, _terminated),
    }
    signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
    try:
        yield
    finally:
        try:
            signal.pthread_sigmask(signal.SIG_UNBLOCK, STOP_SIGNALS)
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)


def uvicorn_config(app: ASGIApp) -> uvicorn.Config:
    """No access log and no `server` header; proxy headers are ignored, since every connection
    comes from this machine. The one WebSocket route runs on wsproto, named so that an installed
    `websockets` package never replaces it, without compression and with messages of at most
    4 MiB."""
    return uvicorn.Config(
        app,
        http="h11",
        ws="wsproto",
        ws_max_size=WEBSOCKET_MESSAGE_LIMIT,
        ws_per_message_deflate=False,
        loop="asyncio",
        lifespan="on",
        log_config=None,
        log_level="warning",
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )


def serve_forever(app: ASGIApp, listener: socket.socket, stopping: Stopping = _nothing) -> None:
    """Serves, inside `stop_signals`, until one of them stops the server; returns only when the
    server did not start. uvicorn handles the signal by shutting down, then raises it again for
    the handlers of `stop_signals`. `stopping` runs first as it shuts down."""
    _Server(uvicorn_config(app), stopping).run(sockets=[listener])


class _Server(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, stopping: Stopping) -> None:
        super().__init__(config)
        self._stopping = stopping

    async def shutdown(self, sockets: list[socket.socket] | None = None) -> None:
        """Runs `stopping` before uvicorn waits for the open responses: a run's stream stays
        open until its child exits, and the children stop only once they are told to. It closes
        the code-intelligence sockets with 1001, before uvicorn closes any with 1012."""
        await self._stopping()
        await super().shutdown(sockets)

    @contextmanager
    def capture_signals(self) -> Generator[None]:
        """Lets the blocked stop signals in once uvicorn's own handlers are in place."""
        with super().capture_signals():
            signal.pthread_sigmask(signal.SIG_UNBLOCK, STOP_SIGNALS)
            yield


def _interrupted(_signal: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def _terminated(_signal: int, _frame: FrameType | None) -> None:
    raise Terminated
