"""A language server as a child process of `cstudy serve`
(docs/specs/web-ui.md#lifecycle-and-limits).

The server runs with no shell, in a session of its own so its whole process group can be stopped,
its standard input and output the LSP stream (`Content-Length` framing, which the WebSocket
messages go without) and its standard error kept. Stopping it is `shutdown`, `exit`, standard
input closed, then SIGTERM and SIGKILL to the group, as a cancelled run escalates; whatever the
server does not read, the stop reaches SIGTERM and SIGKILL on time. A Node server also starts with
`hide_paths.cjs` preloaded, which keeps the hidden directories from it
(docs/specs/web-ui.md#hidden-directories).
"""

import asyncio
import json
import os
import signal
from collections import deque
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from coding_study.domain.code_intelligence import LanguageServer
from coding_study.entrypoints.web.children import StreamedChild, start_process
from coding_study.entrypoints.web.runs import SIGNAL_EXIT_BASE

CONTENT_LENGTH = "content-length"
MESSAGE_LIMIT = 4 * 1024 * 1024
"""The most a message of the server may carry; a longer `Content-Length` ends the output before
the message is read."""
UNREAD_LIMIT = 8 * MESSAGE_LIMIT
"""How many bytes of the server's messages may wait unread, because the page reads slowly."""
PRELOAD = Path(__file__).with_name("hide_paths.cjs")
"""The script that makes the hidden directories not exist for a Node process."""
HIDDEN_VARIABLE = "CSTUDY_HIDDEN_DIRECTORIES"
"""The variable that names those directories to the script: a JSON array of paths."""
SHUTDOWN_ID = "cstudy-shutdown"
"""The id of the broker's own `shutdown` request: ids of its own start with `cstudy-`."""
STDERR_LINES = 20
GROUP_POLL_S = 0.02
KILL_WAIT_S = 2.0
"""How long a group that got SIGKILL has to disappear before the stop gives up on it."""


@dataclass(frozen=True, slots=True)
class LanguageTiming:
    """The clocks of a session."""

    first_message_s: float = 10.0
    """How long a socket has after the upgrade to send the CSRF message."""
    shutdown_wait_s: float = 1.0
    """How long `shutdown` has to be answered before `exit` is sent."""
    terminate_after_s: float = 3.0
    """From the start of the stop to SIGTERM for whatever is left of the process group."""
    kill_after_s: float = 2.0
    """From SIGTERM to SIGKILL."""
    drain_s: float = 1.0
    """How long the output of a server that exited is still read, while a process it left
    behind holds its pipes open."""


@dataclass(frozen=True, slots=True)
class LanguageServerCommand:
    """What starts a server."""

    replacement: tuple[str, ...] | None = None
    """Runs in place of the catalog's command: a test's fake server."""

    def arguments(self, server: LanguageServer, lsp_directory: Path) -> tuple[str, ...]:
        return self.replacement or server.command(str(lsp_directory))


class ServerStartError(Exception):
    """The server could not be started; the text is why, as the 4002 reason says it."""


class _FramingError(Exception):
    """The server's output is not LSP."""


class ServerProcess:
    """A running language server: its messages in and out, its standard error's last line, its
    exit, and the sequence that stops it."""

    def __init__(self, child: StreamedChild, timing: LanguageTiming) -> None:
        self._child = child
        self._timing = timing
        self._messages: asyncio.Queue[tuple[str, int] | None] = asyncio.Queue()
        """The server's messages not yet received, each with its size in bytes."""
        self._unread = 0
        self.backlog = asyncio.Event()
        """Set once more than `UNREAD_LIMIT` bytes of messages waited unread: the output ends."""
        self._stderr: deque[str] = deque(maxlen=STDERR_LINES)
        self._output_ended = False
        self.output_problem: str | None = None
        """Why the output ended before the server did: not LSP."""
        self._tasks = [
            asyncio.create_task(self._read_messages()),
            asyncio.create_task(self._read_stderr()),
        ]
        self._supervising = asyncio.create_task(self._supervise())

    @classmethod
    async def start(
        cls,
        arguments: Sequence[str],
        directory: Path,
        timing: LanguageTiming,
        environment: Mapping[str, str] | None = None,
    ) -> "ServerProcess":
        """Raises ServerStartError, naming what is missing. The server runs in `environment`, by
        default that of `cstudy serve`, as a language server finds its tools as the user's shell
        does."""
        try:
            child = await start_process(
                arguments,
                directory,
                os.environ if environment is None else environment,
                asyncio.subprocess.PIPE,
            )
        except OSError as error:
            raise ServerStartError(_why(error, arguments[0], directory)) from None
        return cls(child, timing)

    @property
    def pid(self) -> int:
        return self._child.pid

    @property
    def running(self) -> bool:
        return self._child.returncode is None

    @property
    def last_error(self) -> str:
        """The last line the server wrote to standard error that holds anything; empty if none."""
        return next((line for line in reversed(self._stderr) if line.strip()), "")

    async def receive(self) -> str | None:
        """The next message the server wrote, as the JSON text it carries; None once its output
        has ended, which is when it exited (after its last messages were read) or wrote what is
        not LSP."""
        waiting = await self._messages.get()
        if waiting is None:
            self._messages.put_nowait(None)
            return None
        text, size = waiting
        self._unread -= size
        return text

    async def send(self, text: str) -> None:
        """Writes one message, framed, and waits until the pipe has taken it, which a server that
        reads nothing never lets it: whoever calls it bounds the wait. A server that is gone gets
        nothing, and a stop ends the wait."""
        body = text.encode()
        self._child.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        with suppress(ConnectionError):
            await self._child.stdin.drain()

    async def exited(self) -> int:
        """Waits for the server to exit; the code a shell reports: 128 plus the number of the
        signal that ended it."""
        returncode = await self._child.exited()
        return returncode if returncode >= 0 else SIGNAL_EXIT_BASE - returncode

    async def stop(self) -> None:
        """Asks the server to exit: `shutdown`, then `exit` once it answered or
        `shutdown_wait_s` passed, then standard input closed, all of it within `terminate_after_s`
        of the start, however little the server reads. A process group that still holds a process
        then gets SIGTERM, and `kill_after_s` later SIGKILL, though the server itself is gone."""
        loop = asyncio.get_running_loop()
        terminate_at = loop.time() + self._timing.terminate_after_s
        with suppress(TimeoutError):
            async with asyncio.timeout_at(terminate_at):
                await self._ask_to_exit()
        self._child.stdin.close()
        if not await self._group_gone(terminate_at):
            self._child.signal_group(signal.SIGTERM)
            if not await self._group_gone(loop.time() + self._timing.kill_after_s):
                self._child.signal_group(signal.SIGKILL)
                await self._group_gone(loop.time() + KILL_WAIT_S)
        await self._finish()

    async def _ask_to_exit(self) -> None:
        if self.running:
            shutdown = {"jsonrpc": "2.0", "id": SHUTDOWN_ID, "method": "shutdown"}
            await self.send(json.dumps(shutdown))
            await self._until_answered(self._timing.shutdown_wait_s)
            await self.send(json.dumps({"jsonrpc": "2.0", "method": "exit"}))

    async def _until_answered(self, seconds: float) -> None:
        """Reads, and drops, what the server writes until it answers `shutdown`, its output
        ends or `seconds` pass."""
        with suppress(TimeoutError):
            async with asyncio.timeout(seconds):
                while (text := await self.receive()) is not None:
                    if _answers_shutdown(text):
                        return

    async def _group_gone(self, deadline: float) -> bool:
        """Whether no process is left in the group by `deadline` (a time of the event loop)."""
        loop = asyncio.get_running_loop()
        while self._child.group_alive():
            if loop.time() >= deadline:
                return False
            await asyncio.sleep(GROUP_POLL_S)
        return True

    async def _finish(self) -> None:
        for task in (*self._tasks, self._supervising):
            task.cancel()
        await asyncio.gather(*self._tasks, self._supervising, return_exceptions=True)
        self._child.close()
        self._end_output()

    async def _supervise(self) -> None:
        """Ends the output once the server exited and what it wrote was read."""
        await self._child.exited()
        _, unfinished = await asyncio.wait(self._tasks, timeout=self._timing.drain_s)
        for task in unfinished:
            task.cancel()
        self._end_output()

    def _drop_backlog(self) -> None:
        """The page does not keep up: what waits is dropped, and the output ends."""
        while not self._messages.empty():
            self._messages.get_nowait()
        self._unread = 0
        self.backlog.set()
        self._end_output()

    def _end_output(self) -> None:
        if not self._output_ended:
            self._output_ended = True
            self._messages.put_nowait(None)

    async def _read_messages(self) -> None:
        try:
            while (body := await _read_frame(self._child.stdout)) is not None:
                text = _decoded(body)
                if self._unread + len(body) > UNREAD_LIMIT:
                    self._drop_backlog()
                    return
                self._unread += len(body)
                self._messages.put_nowait((text, len(body)))
        except _FramingError as error:
            self.output_problem = str(error)
            self._end_output()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass

    async def _read_stderr(self) -> None:
        while True:
            try:
                raw = await self._child.stderr.readline()
            except ValueError:
                continue
            if not raw:
                return
            self._stderr.append(raw.decode(errors="replace").rstrip("\r\n"))


def environment_hiding(
    environment: Mapping[str, str], hidden: Sequence[Path], needed: Sequence[Path]
) -> dict[str, str]:
    """`environment` for a Node server that cannot open the `hidden` directories: `PRELOAD` is
    required by every Node process it starts, and told the directories. A hidden directory that
    holds a `needed` one, such as a content root that holds the workspace, is left out, since the
    server could not work without it."""
    kept = [path for path in hidden if not any(_holds(path, inside) for inside in needed)]
    if not kept:
        return dict(environment)
    options = [environment.get("NODE_OPTIONS", ""), f'--require="{_escaped(PRELOAD)}"']
    return {
        **environment,
        "NODE_OPTIONS": " ".join(option for option in options if option),
        HIDDEN_VARIABLE: json.dumps([str(path) for path in kept]),
    }


def _holds(directory: Path, inside: Path) -> bool:
    return Path(os.path.realpath(inside)).is_relative_to(os.path.realpath(directory))


def _escaped(path: Path) -> str:
    """`path` for inside the double quotes of a value of NODE_OPTIONS."""
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


async def _read_frame(stream: asyncio.StreamReader) -> bytes | None:
    """The body of the next message; None at the end of the output. A `Content-Length` over
    `MESSAGE_LIMIT` is refused before any of the body is read."""
    length: int | None = None
    while True:
        try:
            line = await stream.readline()
        except ValueError:
            raise _FramingError("a header line over the limit") from None
        if not line:
            return None
        header = line.decode("ascii", errors="replace").strip()
        if not header:
            break
        name, _, value = header.partition(":")
        if name.lower() == CONTENT_LENGTH:
            length = _length(value.strip())
    if length is None:
        raise _FramingError("a message without Content-Length")
    return await stream.readexactly(length)


def _decoded(body: bytes) -> str:
    try:
        return body.decode()
    except UnicodeDecodeError:
        raise _FramingError("a message that is not UTF-8") from None


def _length(value: str) -> int:
    if not value.isdecimal():
        raise _FramingError(f"a Content-Length that is not a number: {value}")
    if len(value.lstrip("0")) > len(str(MESSAGE_LIMIT)) or int(value) > MESSAGE_LIMIT:
        raise _FramingError("a message over 4 MiB")
    return int(value)


def _answers_shutdown(text: str) -> bool:
    try:
        message: object = json.loads(text)
    except ValueError:
        return False
    return isinstance(message, dict) and cast(dict[str, object], message).get("id") == SHUTDOWN_ID


def _why(error: OSError, command: str, directory: Path) -> str:
    """What `cannot start:` says: the command that is not there, the directory that is not
    there, or the system's own words."""
    if isinstance(error, FileNotFoundError):
        if str(error.filename) == str(directory):
            return f"no such directory: {directory}"
        return f"{Path(command).name} not found"
    return f"{Path(command).name}: {error.strerror or error}"
