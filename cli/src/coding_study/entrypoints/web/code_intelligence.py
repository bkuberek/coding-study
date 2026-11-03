"""The code-intelligence sessions of the server (docs/specs/web-ui.md#sessions,
docs/specs/web-ui.md#lifecycle-and-limits).

A session is one WebSocket and the language server behind it, started once the page's CSRF message
arrived. Each text message of the socket carries one JSON-RPC message, which this module frames for
the server's standard input and unframes from its standard output. At most four servers run at
once. A session ends when the socket closes, the server exits or the server stops; the stop
sequence of the server runs as a task of its own, so a socket that goes away mid-request never
leaves a process behind.
"""

import asyncio
import json
import sys
from contextlib import suppress
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from coding_study.application.code_intelligence import SessionTarget
from coding_study.entrypoints.web.language_server import (
    LanguageServerCommand,
    LanguageTiming,
    ServerProcess,
    ServerStartError,
)

MAX_SESSIONS = 4
MIB = 1024 * 1024
MESSAGE_LIMIT = 4 * MIB
"""The most a message may carry; uvicorn enforces it on the wire, and the session again."""
REASON_BYTES = 123
"""The most a WebSocket close reason may hold."""
CLOSE_WAIT_S = 2.0
"""How long a server that stops waits for its sockets to close."""
BAD_CSRF = "bad CSRF token"
STOPPING = "cstudy serve is stopping"
PARSE_ERROR = -32700


class CloseCode(IntEnum):
    GOING_AWAY = 1001
    UNSUPPORTED_DATA = 1003
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    SERVER_EXITED = 4002
    TOO_MANY_SESSIONS = 4003


@dataclass(frozen=True, slots=True)
class Closing:
    """How a session closes its socket."""

    code: CloseCode
    reason: str

    async def close(self, websocket: WebSocket) -> None:
        """A socket that is already gone needs no close."""
        with suppress(WebSocketDisconnect, RuntimeError, OSError):
            await websocket.close(self.code, _fitted(self.reason))


def bad_csrf() -> Closing:
    return Closing(CloseCode.POLICY_VIOLATION, BAD_CSRF)


class LanguageSession:
    """A socket and its server, relayed until one of them ends."""

    def __init__(self, websocket: WebSocket, process: ServerProcess) -> None:
        self.websocket = websocket
        self.process = process
        self.finished = asyncio.Event()
        """Set once the session is over: its socket closed and its relays cancelled."""
        self.relays: list[asyncio.Task[Any]] = []
        self._ending: Closing | None = None
        self._wakeup = asyncio.Event()

    def end(self, closing: Closing) -> None:
        """Closes the socket with `closing`, whatever the session is waiting for."""
        self._ending = self._ending or closing
        self._wakeup.set()

    def cancel(self) -> None:
        for relay in self.relays:
            relay.cancel()

    async def run(self) -> None:
        """Until the socket closes, the server ends or `end` is called; closes the socket if
        the end is not the page's own."""
        page = asyncio.create_task(self._from_page())
        server = asyncio.create_task(self._from_server())
        woken = asyncio.create_task(self._wakeup.wait())
        self.relays = [page, server, woken]
        try:
            await asyncio.wait(self.relays, return_when=asyncio.FIRST_COMPLETED)
            closing = self._closing(page, server)
            if closing is not None:
                await closing.close(self.websocket)
        finally:
            self.cancel()
            self.finished.set()

    def _closing(
        self, page: "asyncio.Task[Closing | None]", server: "asyncio.Task[Closing | None]"
    ) -> Closing | None:
        if page.done():
            return page.result()
        return self._ending or (server.result() if server.done() else None)

    async def _from_page(self) -> Closing | None:
        """None once the page closed the socket."""
        while True:
            message = await self.websocket.receive()
            if message["type"] == "websocket.disconnect":
                return None
            text = message.get("text")
            if text is None:
                return Closing(CloseCode.UNSUPPORTED_DATA, "binary messages are not accepted")
            if len(text.encode()) > MESSAGE_LIMIT:
                return Closing(CloseCode.MESSAGE_TOO_BIG, "message over 4 MiB")
            if not _is_object(text):
                await self._reply_parse_error()
                continue
            await self.process.send(text)

    async def _from_server(self) -> Closing | None:
        """None once the page is gone; otherwise the server ended."""
        while (text := await self.process.receive()) is not None:
            try:
                await self.websocket.send_text(text)
            except (WebSocketDisconnect, RuntimeError, OSError):
                return None
        return Closing(CloseCode.SERVER_EXITED, await self._why_it_ended())

    async def _why_it_ended(self) -> str:
        """`exit 1: Error: Cannot find module …`; the output the server wrote that is not LSP."""
        if self.process.output_problem is not None:
            return f"bad output: {self.process.output_problem}"
        reason = f"exit {await self.process.exited()}"
        line = self.process.last_error
        return f"{reason}: {line}" if line else reason

    async def _reply_parse_error(self) -> None:
        error = {"code": PARSE_ERROR, "message": "not one JSON object"}
        reply = {"jsonrpc": "2.0", "id": None, "error": error}
        with suppress(WebSocketDisconnect, RuntimeError, OSError):
            await self.websocket.send_text(json.dumps(reply))


class LanguageSessions:
    """Every session of the server, and the servers' slots: at most `limit` run at once, and a
    server holds its slot until its process has exited."""

    def __init__(
        self,
        command: LanguageServerCommand | None = None,
        timing: LanguageTiming | None = None,
        limit: int = MAX_SESSIONS,
    ) -> None:
        self.command = command or LanguageServerCommand()
        self.timing = timing or LanguageTiming()
        self._limit = limit
        self._starting = asyncio.Lock()
        self._stopping = False
        self._servers: set[ServerProcess] = set()
        self._sessions: set[LanguageSession] = set()
        self._stoppers: set[asyncio.Task[None]] = set()

    async def serve(self, websocket: WebSocket, target: SessionTarget) -> None:
        """Starts the target's server and relays the socket to it until either ends; the socket
        closes with 4003 while `limit` servers run, 4002 when the server cannot start and 1001
        once the server is stopping."""
        session = await self._open(websocket, target)
        if session is None:
            return
        try:
            await session.run()
        finally:
            self._release(session)

    async def stop(self) -> None:
        """Closes every socket with 1001 and stops every server, waiting for the last of them;
        no session starts from now on."""
        async with self._starting:
            self._stopping = True
        sessions = list(self._sessions)
        for session in sessions:
            session.end(Closing(CloseCode.GOING_AWAY, STOPPING))
        with suppress(TimeoutError):
            await asyncio.wait_for(_finished(sessions), CLOSE_WAIT_S)
        for session in list(self._sessions):
            self._release(session)
        while self._stoppers:
            await asyncio.gather(*self._stoppers)

    async def _open(self, websocket: WebSocket, target: SessionTarget) -> LanguageSession | None:
        async with self._starting:
            refusal = self._refusal()
            if refusal is None:
                arguments = self.command.arguments(target.server, target.lsp_directory)
                try:
                    process = await ServerProcess.start(arguments, target.directory, self.timing)
                except ServerStartError as error:
                    refusal = Closing(CloseCode.SERVER_EXITED, f"cannot start: {error}")
                else:
                    return self._admit(LanguageSession(websocket, process))
        await refusal.close(websocket)
        return None

    def _refusal(self) -> Closing | None:
        if self._stopping:
            return Closing(CloseCode.GOING_AWAY, STOPPING)
        if sum(1 for server in self._servers if server.running) >= self._limit:
            reason = f"at most {self._limit} code intelligence sessions run at once; "
            return Closing(CloseCode.TOO_MANY_SESSIONS, reason + "close one in another tab")
        return None

    def _admit(self, session: LanguageSession) -> LanguageSession:
        self._servers.add(session.process)
        self._sessions.add(session)
        return session

    def _release(self, session: LanguageSession) -> None:
        """Ends the session's relays and stops its server in a task of its own, which outlives
        a handler that is cancelled. Once only."""
        if session not in self._sessions:
            return
        self._sessions.discard(session)
        session.cancel()
        stopper = asyncio.create_task(self._stop_server(session))
        self._stoppers.add(stopper)
        stopper.add_done_callback(self._stoppers.discard)

    async def _stop_server(self, session: LanguageSession) -> None:
        try:
            await asyncio.gather(*session.relays, return_exceptions=True)
            await session.process.stop()
        except Exception as error:  # the other servers go on; this one is reported
            print(f"cstudy serve: cannot stop a language server cleanly: {error}", file=sys.stderr)
        finally:
            self._servers.discard(session.process)


async def _finished(sessions: list[LanguageSession]) -> None:
    await asyncio.gather(*(session.finished.wait() for session in sessions))


def _is_object(text: str) -> bool:
    try:
        return isinstance(json.loads(text), dict)
    except (ValueError, RecursionError):
        return False


def _fitted(reason: str) -> str:
    """`reason` cut to a WebSocket close reason's 123 bytes, at a character boundary."""
    return reason.encode()[:REASON_BYTES].decode(errors="ignore")
