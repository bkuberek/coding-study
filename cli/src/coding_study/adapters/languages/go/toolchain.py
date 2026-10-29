"""Running the `go` command for the Go runner's build (docs/specs/runners.md#go-build-details)."""

import fcntl
import os
import subprocess
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.domain.errors import RunnerStartError

GO = "go"
GO_ENVIRONMENT = {
    "GOTOOLCHAIN": "local",
    "GOPROXY": "off",
    "GOFLAGS": "",
    "GO111MODULE": "on",
}
"""Never download a toolchain or a module, and ignore the user's GOFLAGS: builds work offline."""
MISSING_GO = "go was not found on PATH; --lang go needs Go 1.24 or newer"


@dataclass(frozen=True, slots=True)
class GoOutcome:
    exit_code: int
    stdout: str
    stderr: str


class GoToolchain(Protocol):
    """The `go` operations the Go runner needs; tests substitute a fake."""

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> GoOutcome:
        """`go build <arguments>` in `cwd` with `environment` added to the process's own.

        Raises RunnerStartError when `go` cannot be started at all.
        """
        ...


class SubprocessGo:
    """`GoToolchain` backed by the `go` command on PATH."""

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> GoOutcome:
        try:
            completed = subprocess.run(
                [GO, "build", *arguments],
                cwd=cwd,
                env={**os.environ, **GO_ENVIRONMENT, **environment},
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            raise RunnerStartError(MISSING_GO) from None
        except OSError as error:
            raise RunnerStartError(f"cannot run go: {error.strerror or error}") from error
        return GoOutcome(
            completed.returncode,
            completed.stdout.decode("utf-8", errors="replace"),
            completed.stderr.decode("utf-8", errors="replace"),
        )


@contextmanager
def exclusive(lock_file: Path) -> Generator[None]:
    """Holds an exclusive lock on `lock_file` (created when missing), so two `cstudy` processes
    never write the same generated files or build output at once."""
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)
