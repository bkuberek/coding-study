"""The `cstudy` commands the server starts as child processes (docs/specs/web-ui.md#process).

A child is the same install as the server, given the server's workspace and content, started in a
session of its own, in the workspace, with nothing on its standard input, no colour and 120
columns. The argument list is built here, never by a shell. `start_process` also starts the
language servers of the code-intelligence sessions, in the same way.
"""

import asyncio
import os
import signal
import sys
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

CHILD_ENVIRONMENT = {"NO_COLOR": "1", "COLUMNS": "120"}


def _this_install() -> tuple[str, ...]:
    return (sys.executable, "-m", "coding_study")


@dataclass(frozen=True, slots=True)
class ChildCommand:
    content: Path | None = None
    """The `--content` the server was started with, passed on to every child."""
    interpreter: tuple[str, ...] = field(default_factory=_this_install)
    """What runs `cstudy`: `python -m coding_study` of the server's own interpreter."""

    def arguments(self, workspace: Path, command: Sequence[str]) -> list[str]:
        content = ("--content", str(self.content)) if self.content else ()
        return [*self.interpreter, "--workspace", str(workspace), *content, *command]


@dataclass(frozen=True, slots=True)
class ChildResult:
    exit_code: int
    stdout: str
    stderr: str


class ChildDeadlineError(Exception):
    """The child ran past its deadline and was killed."""


async def run_child(
    child: ChildCommand, workspace: Path, command: Sequence[str], deadline_s: float
) -> ChildResult:
    """Runs a child to its end; raises ChildDeadlineError, killing its process group, when it
    runs longer than `deadline_s`."""
    process = await asyncio.create_subprocess_exec(
        *child.arguments(workspace, command),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=workspace,
        env={**os.environ, **CHILD_ENVIRONMENT},
        start_new_session=True,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), deadline_s)
    except TimeoutError:
        os.killpg(process.pid, signal.SIGKILL)
        await process.wait()
        raise ChildDeadlineError from None
    assert process.returncode is not None
    return ChildResult(process.returncode, stdout.decode(), stderr.decode())


LINE_LIMIT = 16 * 1024 * 1024
"""The longest line a streamed child may write: a `run_end` carries a whole `--json` document."""


class _ExitProtocol(asyncio.subprocess.SubprocessStreamProtocol):
    """Tells when the process exits, which `Process.wait` does only once its pipes close too."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(limit=LINE_LIMIT, loop=loop)
        self.exited = asyncio.Event()

    def process_exited(self) -> None:
        super().process_exited()
        self.exited.set()


@dataclass(frozen=True, slots=True)
class StreamedChild:
    """A child whose output is read line by line as it comes."""

    transport: asyncio.SubprocessTransport
    protocol: _ExitProtocol

    @property
    def stdout(self) -> asyncio.StreamReader:
        assert self.protocol.stdout is not None
        return self.protocol.stdout

    @property
    def stderr(self) -> asyncio.StreamReader:
        assert self.protocol.stderr is not None
        return self.protocol.stderr

    @property
    def stdin(self) -> asyncio.StreamWriter:
        """The writer of a process started with a pipe for standard input."""
        assert self.protocol.stdin is not None
        return self.protocol.stdin

    @property
    def pid(self) -> int:
        return self.transport.get_pid()

    @property
    def returncode(self) -> int | None:
        """The process's status once it exited: negative for the signal that ended it."""
        return self.transport.get_returncode()

    async def exited(self) -> int:
        """Waits for the process to exit, even while a process it left behind holds its pipes."""
        await self.protocol.exited.wait()
        returncode = self.returncode
        assert returncode is not None
        return returncode

    def send(self, number: signal.Signals) -> None:
        """Sends a signal to the process while it runs, and to nothing else."""
        if self.returncode is None:
            with suppress(ProcessLookupError):
                os.kill(self.transport.get_pid(), number)

    def kill_group(self) -> None:
        """SIGKILL to the process and everything still in its process group."""
        if self.returncode is None:
            with suppress(ProcessLookupError):
                os.killpg(self.transport.get_pid(), signal.SIGKILL)

    def group_alive(self) -> bool:
        """Whether any process is left in the child's process group: the child itself, or one it
        started and left running after it exited."""
        try:
            os.killpg(self.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def signal_group(self, number: signal.Signals) -> None:
        """A signal to everything in the process group, whether or not the child itself runs."""
        with suppress(ProcessLookupError):
            os.killpg(self.pid, number)

    def close(self) -> None:
        """Closes the pipes, which a process the child left behind may still hold."""
        self.transport.close()


async def start_child(
    child: ChildCommand, workspace: Path, command: Sequence[str]
) -> StreamedChild:
    return await start_process(
        child.arguments(workspace, command),
        workspace,
        {**os.environ, **CHILD_ENVIRONMENT},
        asyncio.subprocess.DEVNULL,
    )


async def start_piped_child(
    child: ChildCommand, workspace: Path, command: Sequence[str]
) -> StreamedChild:
    """`start_child`, with a pipe on standard input that the server writes lines to."""
    return await start_process(
        child.arguments(workspace, command),
        workspace,
        {**os.environ, **CHILD_ENVIRONMENT},
        asyncio.subprocess.PIPE,
    )


async def start_process(
    arguments: Sequence[str], directory: Path, environment: Mapping[str, str], stdin: int
) -> StreamedChild:
    """`arguments` in `directory`, in a session of its own, so its whole process group can be
    stopped; `stdin` is `asyncio.subprocess.PIPE` or `DEVNULL`. Raises OSError when it cannot
    start."""
    loop = asyncio.get_running_loop()
    protocol = _ExitProtocol(loop)
    transport, _ = await loop.subprocess_exec(
        lambda: protocol,
        *arguments,
        stdin=stdin,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=directory,
        env=dict(environment),
        start_new_session=True,
    )
    return StreamedChild(transport, protocol)
