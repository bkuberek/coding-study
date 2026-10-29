"""Running the `go` command for the Go runner's build (docs/specs/runners.md#go-build-details)."""

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.domain.errors import RunnerStartError

GO = "go"
GO_ENVIRONMENT = {
    "GOENV": "off",
    "GOTOOLCHAIN": "local",
    "GOPROXY": "off",
    "GOFLAGS": "-mod=readonly",
    "GO111MODULE": "on",
}
"""Never download a toolchain or a module, and build for this machine whatever the user's Go
settings say: `GOENV=off` ignores the file `go env -w` writes, and `GOFLAGS` is set explicitly
because the go command treats an empty value as unset."""
USER_GO_SETTINGS = frozenset({"GOOS", "GOARCH", "GOWORK"})
"""Variables of the user's environment that would build for another platform or another
workspace; the build leaves them out (it sets its own GOWORK)."""
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
                env=build_environment(os.environ, environment),
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


def build_environment(inherited: Mapping[str, str], build: Mapping[str, str]) -> dict[str, str]:
    """The process environment of `go build`: `inherited` without the user's platform and
    workspace settings, then the fixed settings, then `build`'s."""
    kept = {name: value for name, value in inherited.items() if name not in USER_GO_SETTINGS}
    return {**kept, **GO_ENVIRONMENT, **build}
