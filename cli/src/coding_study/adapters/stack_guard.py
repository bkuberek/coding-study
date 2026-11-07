"""Takes a stack down once `cstudy` dies, however it dies (docs/specs/service-projects.md#leftovers).

Containers outlive their owner: a SIGKILL leaves them running and holding memory, and `OrphanGuard`
kills processes, not containers. This guard reads its standard input, a pipe whose writing end only
`cstudy` holds, until the pipe ends, which the kernel does when `cstudy` exits; it then runs
`docker compose -p <stack> down`, with `-v` for a test or a graded stack. Nothing polls.

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
from types import TracebackType
from typing import IO, Self

DOCKER = "docker"
REMOVE_VOLUMES = "-v"
_GUARD_READ_BYTES = 4096
_DOWN_TIMEOUT_S = 300.0


class StackGuard:
    """`release` kills the guard and only then closes the pipe, so a stack `cstudy` stopped itself
    is left alone. Start it before the stack, and release it after the stack's `down`, so a
    `cstudy` that dies during that cleanup still leaves nothing behind."""

    def __init__(
        self, stack: str, *, removes_volumes: bool, environment: Mapping[str, str]
    ) -> None:
        docker = shutil.which(DOCKER, path=environment.get("PATH")) or DOCKER
        flags = (REMOVE_VOLUMES,) if removes_volumes else ()
        self._process = subprocess.Popen(
            [sys.executable, "-I", "-S", __file__, docker, stack, *flags],
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
    docker, stack, *flags = arguments
    with suppress(OSError):
        while os.read(sys.stdin.fileno(), _GUARD_READ_BYTES):
            pass
    with suppress(OSError, subprocess.SubprocessError):
        subprocess.run(
            [docker, "compose", "-p", stack, "down", *flags],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_DOWN_TIMEOUT_S,
            check=False,
        )


if __name__ == "__main__":
    _guard(sys.argv[1:])
