"""Takes a stack down once `cstudy` dies, however it dies
(docs/specs/service-projects.md#leftovers).

Containers outlive their owner: a SIGKILL leaves them running and holding memory, and `OrphanGuard`
kills processes, not containers. This guard reads its standard input, a pipe whose writing end only
`cstudy` holds, until the pipe ends, which the kernel does when `cstudy` exits; it then removes the
stack's one-offs, runs `docker compose -p <stack> down`, with `-v` for a test or a graded stack, and
removes the run's folder. Nothing polls.

Run as a script, this file is the process of a guard. It imports only the standard library, so
that process starts in a few milliseconds without `site` and needs nothing installed. The sweep
still covers the case where the guard itself dies.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import IO, Self

DOCKER = "docker"
REMOVE_VOLUMES = "-v"
NO_RUN_FOLDER = "-"
_GUARD_READ_BYTES = 4096
_DOWN_TIMEOUT_S = 300.0


def one_off_filters(stack: str) -> tuple[str, ...]:
    """What `docker ps` finds a stack's one-offs by: `docker compose run` containers, cstudy's, of
    this stack. A one-off whose client died runs on, and `docker compose down` leaves it and its
    network and exits 0, with `--remove-orphans` too unless the stack's file is named, so it goes
    by these labels first. Here, since a guard's process imports only the standard library."""
    return (
        *("--filter", f"label=com.docker.compose.project={stack}"),
        *("--filter", "label=com.docker.compose.oneoff=True"),
        *("--filter", "label=cstudy.kind"),
    )


class StackGuard:
    """`release` kills the guard and only then closes the pipe, so a stack `cstudy` stopped itself
    is left alone. Start it before the stack, and release it after the stack's `down`, so a
    `cstudy` that dies during that cleanup still leaves nothing behind."""

    def __init__(
        self,
        stack: str,
        *,
        removes_volumes: bool,
        environment: Mapping[str, str],
        run_directory: Path | None = None,
    ) -> None:
        docker = shutil.which(DOCKER, path=environment.get("PATH")) or DOCKER
        run = NO_RUN_FOLDER if run_directory is None else str(run_directory)
        flags = (REMOVE_VOLUMES,) if removes_volumes else ()
        self._process = subprocess.Popen(
            [sys.executable, "-I", "-S", __file__, docker, stack, run, *flags],
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=dict(environment),
        )
        assert self._process.stdin is not None
        self._pipe: IO[bytes] = self._process.stdin

    def release(self) -> None:
        self._process.kill()
        self._process.wait()
        self._pipe.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _type: type[BaseException] | None,
        _error: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.release()


def _guard(arguments: Sequence[str]) -> None:
    """The guard's process: once standard input ends, the stack comes down."""
    docker, stack, run, *flags = arguments
    with suppress(OSError):
        while os.read(sys.stdin.fileno(), _GUARD_READ_BYTES):
            pass
    one_offs = _output_of([docker, "ps", "-aq", *one_off_filters(stack)]).split()
    if one_offs:
        _output_of([docker, "rm", "-f", "-v", *one_offs])
    _output_of([docker, "compose", "-p", stack, "down", *flags])
    if run != NO_RUN_FOLDER:
        shutil.rmtree(run, ignore_errors=True)


def _output_of(command: Sequence[str]) -> str:
    """Empty when it did not run: the next step is still worth trying."""
    with suppress(OSError, subprocess.SubprocessError):
        return subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
            timeout=_DOWN_TIMEOUT_S,
            check=False,
        ).stdout
    return ""


if __name__ == "__main__":
    _guard(sys.argv[1:])
