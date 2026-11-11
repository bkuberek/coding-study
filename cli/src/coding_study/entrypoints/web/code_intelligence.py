"""The code-intelligence sessions of the server (docs/specs/web-ui.md#sessions,
docs/specs/web-ui.md#lifecycle-and-limits).

A session is one WebSocket and the language server behind it, started once the page's CSRF message
arrived. Each text message of the socket carries one JSON-RPC message, which this module frames for
the server's standard input and unframes from its standard output; what each becomes is the
session's broker's to say (`language_broker.py`). At most four servers run at once. A server that
keeps data, JDT LS, gets a data directory of its root under `.cs/lsp/` that no running server
holds, since two cannot share one. A service project's server runs in a sidecar container of its
own, through `docker exec`, and the sidecar goes once the server has stopped
(docs/specs/service-projects.md#language-servers). A session ends when the socket closes, the
server exits or the server stops; the stop sequence of the server runs as a task of its own, so a
socket that goes away mid-request never leaves a process behind. What waits for a side that stopped
reading is bounded: a server that reads none of its input, or a page that reads none of the
server's messages, ends the session.
"""

import asyncio
import itertools
import json
import sys
from collections.abc import Callable
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, cast

from starlette.websockets import WebSocket, WebSocketDisconnect

from coding_study.adapters.docker_sandbox import DockerSandbox
from coding_study.adapters.process_environment import docker_environment, inherited_environment
from coding_study.application.attempt_changes import FileChanged
from coding_study.application.code_intelligence import SessionTarget, sidecar_unavailable
from coding_study.application.ports import SidecarEngine
from coding_study.domain.code_intelligence import SIDECAR_PLATFORM, Launch
from coding_study.domain.errors import SandboxError
from coding_study.domain.sandbox import SidecarPlan
from coding_study.entrypoints.web.language_broker import Delivery, LanguageBroker
from coding_study.entrypoints.web.language_server import (
    LanguageServerCommand,
    LanguageTiming,
    ServerProcess,
    ServerStartError,
    environment_hiding,
    prepare_data_directory,
    prepare_standard_library,
)
from coding_study.entrypoints.web.notifications import Notifications

MAX_SESSIONS = 4
MIB = 1024 * 1024
MESSAGE_LIMIT = 4 * MIB
"""The most a message may carry; uvicorn enforces it on the wire, and the session again."""
OUTBOX_LIMIT = 8 * MESSAGE_LIMIT
"""How many bytes of messages may wait for a server that does not read its input."""
REASON_BYTES = 123
"""The most a WebSocket close reason may hold."""
CLOSE_WAIT_S = 2.0
"""How long a server that stops waits for its sockets to close."""
BAD_CSRF = "bad CSRF token"
STOPPING = "cstudy serve is stopping"
SERVER_STUCK = "stuck: the server does not read its input"
PAGE_LAGGING = "the page does not read the server's messages"
PARSE_ERROR = -32700


class CloseCode(IntEnum):
    GOING_AWAY = 1001
    UNSUPPORTED_DATA = 1003
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    SERVER_EXITED = 4002
    TOO_MANY_SESSIONS = 4003
    NEEDS_DOCKER = 4004
    """A service project's server cannot start: Docker does not answer, or the sidecar's image is
    not here. The page shows it calmly, since nothing failed."""


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


class _NoSidecarError(Exception):
    """A service project's server cannot start now; the text says why, as 4004's reason."""


class LanguageSession:
    """A socket and its server, relayed until one of them ends, through the broker."""

    def __init__(
        self,
        websocket: WebSocket,
        process: ServerProcess,
        broker: LanguageBroker,
        data_directory: str | None = None,
        sidecar: ExitStack | None = None,
    ) -> None:
        self.websocket = websocket
        self.process = process
        self.data_directory = data_directory
        """The data directory the server holds until it has exited, for a server that keeps
        data."""
        self.sidecar = sidecar
        """Holds a service project's sidecar up until the server has stopped."""
        self.finished = asyncio.Event()
        """Set once the session is over: its socket closed and its relays cancelled."""
        self.relays: list[asyncio.Task[Any]] = []
        self.stop_listening: Callable[[], None] = _nothing
        """Ends the session's hearing of the workspace's file changes."""
        self._broker = broker
        self._ending: Closing | None = None
        self._wakeup = asyncio.Event()
        self._outbox: asyncio.Queue[str] = asyncio.Queue()
        """What goes to the server, in order: the page's messages, the broker's answers to the
        server's requests, and the file changes."""
        self._queued = 0
        """The bytes in the outbox: over `OUTBOX_LIMIT` the session ends."""

    def end(self, closing: Closing) -> None:
        """Closes the socket with `closing`, whatever the session is waiting for."""
        self._ending = self._ending or closing
        self._wakeup.set()

    def cancel(self) -> None:
        """Ends the relays and the hearing of file changes; once is enough."""
        stop, self.stop_listening = self.stop_listening, _nothing
        stop()
        for relay in self.relays:
            relay.cancel()

    def file_changed(self, change: FileChanged) -> None:
        """A file of an attempt changed on disk; the server hears of it if it asked to."""
        self._send_to_server(self._broker.file_changed(change))

    async def run(self) -> None:
        """Until the socket closes, the server ends or `end` is called; closes the socket if
        the end is not the page's own."""
        page = asyncio.create_task(self._from_page())
        server = asyncio.create_task(self._from_server())
        writing = asyncio.create_task(self._to_server())
        woken = asyncio.create_task(self._wakeup.wait())
        lagging = asyncio.create_task(self._end_when_page_lags())
        self.relays = [page, server, writing, woken, lagging]
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
            fields = _object(text)
            if fields is None:
                await self._reply_parse_error()
                continue
            if not await self._deliver(await self._broker.from_page(fields)):
                return None

    async def _from_server(self) -> Closing | None:
        """None once the page is gone; otherwise the server ended."""
        while (text := await self.process.receive()) is not None:
            if not await self._deliver(self._broker.from_server(text)):
                return None
        return Closing(CloseCode.SERVER_EXITED, await self._why_it_ended())

    async def _to_server(self) -> None:
        while True:
            text = await self._outbox.get()
            self._queued -= len(text)
            await self.process.send(text)

    async def _end_when_page_lags(self) -> None:
        await self.process.backlog.wait()
        self.end(Closing(CloseCode.POLICY_VIOLATION, PAGE_LAGGING))

    async def _deliver(self, delivery: Delivery) -> bool:
        """False once the page is gone."""
        self._send_to_server(delivery)
        try:
            for message in delivery.to_page:
                await self.websocket.send_text(json.dumps(message))
        except (WebSocketDisconnect, RuntimeError, OSError):
            return False
        return True

    def _send_to_server(self, delivery: Delivery) -> None:
        for message in delivery.to_server:
            text = json.dumps(message)
            if self._ending is not None:
                return
            if self._queued + len(text) > OUTBOX_LIMIT:
                self.end(Closing(CloseCode.SERVER_EXITED, SERVER_STUCK))
                return
            self._queued += len(text)
            self._outbox.put_nowait(text)

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
        *,
        sidecars: SidecarEngine | None = None,
    ) -> None:
        self.command = command or LanguageServerCommand()
        self.timing = timing or LanguageTiming()
        self._limit = limit
        self._sidecars = sidecars or DockerSandbox()
        """Where a service project's server runs."""
        self._starting = asyncio.Lock()
        self._stopping = False
        self._servers: set[ServerProcess] = set()
        self._sessions: set[LanguageSession] = set()
        self._held_data: dict[str, ServerProcess] = {}
        """The server that last held each data directory, which holds it until it has exited."""
        self._stoppers: set[asyncio.Task[None]] = set()
        self._notifications: Notifications | None = None

    def watch(self, notifications: Notifications) -> None:
        """From now on each session hears the file changes of `notifications`."""
        self._notifications = notifications

    async def serve(
        self, websocket: WebSocket, target: SessionTarget, broker: LanguageBroker
    ) -> None:
        """Starts the target's server and relays the socket to it, through `broker`, until either
        ends; the socket closes with 4003 while `limit` servers run, 4002 when the server cannot
        start, 4004 when a service project's cannot start yet, and 1001 once the server is
        stopping."""
        session = await self._open(websocket, target, broker)
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

    async def _open(
        self, websocket: WebSocket, target: SessionTarget, broker: LanguageBroker
    ) -> LanguageSession | None:
        async with self._starting:
            refusal = self._refusal()
            if refusal is None:
                launch = self._launch(target)
                try:
                    process, sidecar = await self._start(target, launch)
                except ServerStartError as error:
                    refusal = Closing(CloseCode.SERVER_EXITED, f"cannot start: {error}")
                except _NoSidecarError as error:
                    refusal = Closing(CloseCode.NEEDS_DOCKER, str(error))
                else:
                    data = launch.data_directory
                    session = LanguageSession(websocket, process, broker, data, sidecar)
                    return self._admit(session)
        await refusal.close(websocket)
        return None

    def _launch(self, target: SessionTarget) -> Launch:
        """The places the target's command names; a server that keeps data gets the first data
        directory of its root that no running server of this `cstudy serve` holds, since two
        servers cannot share one. A server in a sidecar runs on Linux, on the image's `java`, with
        the sidecar's own data folder, which no other session sees."""
        lsp = target.lsp_directory
        if target.sidecar is not None:
            data = target.sidecar.data_directory
            return Launch(str(lsp), data, platform=SIDECAR_PLATFORM)
        home = None if target.java_home is None else str(target.java_home)
        java = None if target.java_home is None else str(target.java_home / "bin" / "java")
        data = None
        if target.server.data is not None:
            data = self._free_data_directory(lsp / target.server.data / target.root)
        return Launch(str(lsp), data, java, sys.platform, home)

    def _free_data_directory(self, base: Path) -> str:
        places = (str(base / str(slot)) for slot in itertools.count(1))
        return next(place for place in places if not self._is_held(place))

    def _is_held(self, data_directory: str) -> bool:
        holder = self._held_data.get(data_directory)
        return holder is not None and holder.running

    async def _start(
        self, target: SessionTarget, launch: Launch
    ) -> tuple[ServerProcess, ExitStack | None]:
        """The server, and what holds its sidecar up for a service project. Raises
        ServerStartError, and _NoSidecarError."""
        if target.sidecar is not None:
            return await self._start_in_sidecar(target, target.sidecar, launch)
        return await self._start_here(target, launch), None

    async def _start_in_sidecar(
        self, target: SessionTarget, plan: SidecarPlan, launch: Launch
    ) -> tuple[ServerProcess, ExitStack]:
        """The engine is never started and the image never pulled for a session, which says
        calmly why it cannot start. The server runs with its own variables but none that hides
        directories, since none of them is mounted; a sidecar whose server does not start goes at
        once."""
        unavailable = await asyncio.to_thread(sidecar_unavailable, self._sidecars, plan.image)
        if unavailable is not None:
            raise _NoSidecarError(unavailable)
        sidecar = ExitStack()
        try:
            await asyncio.to_thread(sidecar.enter_context, self._sidecars.sidecar(plan))
            await asyncio.to_thread(prepare_data_directory, target.server, launch)
            server = target.server
            command = self.command.arguments(server, launch)
            arguments = self._sidecars.sidecar_command(plan, command, server.environment(launch))
            environment = docker_environment()
            process = await ServerProcess.start(
                arguments, target.directory, self.timing, environment
            )
        except (SandboxError, OSError) as error:
            await asyncio.to_thread(sidecar.close)
            raise ServerStartError(str(error)) from None
        except BaseException:
            await asyncio.to_thread(sidecar.close)
            raise
        return process, sidecar

    async def _start_here(self, target: SessionTarget, launch: Launch) -> ServerProcess:
        """Raises ServerStartError."""
        server = target.server
        needed = (target.directory, target.lsp_directory)
        hiding = environment_hiding(inherited_environment(), target.hidden, needed)
        environment = {**hiding, **server.environment(launch)}
        try:
            await asyncio.to_thread(prepare_data_directory, server, launch)
        except OSError as error:
            raise ServerStartError(f"cannot write {launch.data_directory}: {error}") from None
        try:
            await asyncio.to_thread(prepare_standard_library, target, environment)
        except OSError as error:
            links = target.standard_library_links
            raise ServerStartError(
                f"cannot link the standard library in {links}: {error}"
            ) from None
        arguments = self.command.arguments(server, launch)
        return await ServerProcess.start(arguments, target.directory, self.timing, environment)

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
        if session.data_directory is not None:
            self._held_data[session.data_directory] = session.process
        if self._notifications is not None:
            session.stop_listening = self._notifications.on_file_changed(session.file_changed)
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
            if session.sidecar is not None:
                await asyncio.to_thread(session.sidecar.close)


async def _finished(sessions: list[LanguageSession]) -> None:
    await asyncio.gather(*(session.finished.wait() for session in sessions))


def _object(text: str) -> dict[str, Any] | None:
    """The JSON object `text` carries; None if it carries anything else."""
    try:
        document: object = json.loads(text)
    except (ValueError, RecursionError):
        return None
    return cast(dict[str, Any], document) if isinstance(document, dict) else None


def _nothing() -> None:
    pass


def _fitted(reason: str) -> str:
    """`reason` cut to a WebSocket close reason's 123 bytes, at a character boundary."""
    return reason.encode()[:REASON_BYTES].decode(errors="ignore")
