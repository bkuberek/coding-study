"""Runs the app on uvicorn, on a socket bound to the loopback address before the app exists, so
the port the system picks for `--port 0` is known to the session (docs/specs/web-ui.md#server).
"""

import errno
import signal
import socket
from collections.abc import Generator
from contextlib import contextmanager
from types import FrameType

import uvicorn
from starlette.types import ASGIApp

from coding_study.entrypoints.web.security import LOOPBACK

STOP_SIGNALS = frozenset({signal.SIGINT, signal.SIGTERM})


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


def serve_forever(app: ASGIApp, listener: socket.socket) -> None:
    """Serves, inside `stop_signals`, until one of them stops the server; returns only when the
    server did not start. uvicorn handles the signal by shutting down, then raises it again for
    the handlers of `stop_signals`.

    No access log and no `server` header; proxy headers are ignored, since every connection
    comes from this machine."""
    config = uvicorn.Config(
        app,
        http="h11",
        ws="none",
        loop="asyncio",
        lifespan="on",
        log_config=None,
        log_level="warning",
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )
    _Server(config).run(sockets=[listener])


class _Server(uvicorn.Server):
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
