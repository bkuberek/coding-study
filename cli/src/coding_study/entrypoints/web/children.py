"""The `cstudy` commands the server starts as child processes (docs/specs/web-ui.md#process).

A child is the same install as the server, given the server's workspace and content, started in a
session of its own, in the workspace, with nothing on its standard input, no colour and 120
columns. The argument list is built here, never by a shell.
"""

import asyncio
import os
import signal
import sys
from collections.abc import Sequence
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
