"""Running the `go` command for the Go runner's build (docs/specs/runners.md#go-build-details)."""

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.adapters.languages.bounded_process import (
    DEFAULT_BUILD_TIMEOUT_SECONDS,
    BoundedProcess,
)
from coding_study.domain.errors import RunnerStartError

GO = "go"
GO_ENVIRONMENT = {
    "GOENV": "off",
    "GOTOOLCHAIN": "local",
    "GOPROXY": "off",
    "GOFLAGS": "-mod=readonly",
    "GO111MODULE": "on",
    "CGO_ENABLED": "0",
}
"""Never download a toolchain or a module, and build for this machine whatever the user's Go
settings say: `GOENV=off` ignores the file `go env -w` writes, and `GOFLAGS` is set explicitly
because the go command treats an empty value as unset. Without cgo no C compiler is ever run, so
a user's `CC` or a missing one cannot break a build."""
PLATFORM_SETTINGS = frozenset(
    {
        *("GOOS", "GOARCH", "GOEXPERIMENT", "GOFIPS140"),
        *("GOAMD64", "GOARM", "GOARM64", "GO386", "GOMIPS", "GOMIPS64", "GOPPC64", "GORISCV64"),
    }
)
"""Variables that build for another platform, or for another instruction-set level or
experiment of this one, which changes the code a benchmark measures."""
UNSET_PLATFORM_SETTINGS = dict.fromkeys(sorted(PLATFORM_SETTINGS), "")
"""For a process started later (the suite runner's `go test`): the go command reads each of
these as unset when empty."""
USER_GO_SETTINGS = frozenset({*PLATFORM_SETTINGS, "GOWORK", "CC", "CXX"})
USER_GO_PREFIXES = ("CGO_",)
"""Variables of the user's environment that would build for another platform or workspace, or
configure cgo; the build leaves them out (it sets its own GOWORK and CGO_ENABLED)."""
BUILD_STEP = "go build"
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
    """`GoToolchain` backed by the `go` command on PATH, stopped when a build outlives
    `timeout_seconds` (docs/specs/runners.md#build-timeouts)."""

    def __init__(self, timeout_seconds: float = DEFAULT_BUILD_TIMEOUT_SECONDS) -> None:
        self._process = BoundedProcess(BUILD_STEP, timeout_seconds)

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> GoOutcome:
        try:
            completed = self._process.run(
                [GO, "build", *arguments], cwd, build_environment(os.environ, environment)
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
    """The process environment of `go build`: `inherited` without the user's platform, workspace
    and cgo settings, then the fixed settings, then `build`'s."""
    kept = {
        name: value
        for name, value in inherited.items()
        if name not in USER_GO_SETTINGS and not name.startswith(USER_GO_PREFIXES)
    }
    return {**kept, **GO_ENVIRONMENT, **build}
