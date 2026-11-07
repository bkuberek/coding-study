"""Running `cargo` and `rustc` for the Rust runner's build
(docs/specs/runners.md#rust-build-details).

The user's Cargo setup must neither break nor redirect a build: the build pins the target
directory, the target triple, the compiler, the linker, the release profile's semantics, and runs
without rustflags or a `rustc` wrapper, whatever the environment or a `config.toml` says.
"""

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.adapters.languages.bounded_process import (
    DEFAULT_BUILD_TIMEOUT_SECONDS,
    BoundedProcess,
)
from coding_study.adapters.process_environment import inherited_environment
from coding_study.domain.errors import RunnerStartError

CARGO = "cargo"
RUSTC = "rustc"
MISSING_CARGO = "cargo was not found on PATH; --lang rust needs Rust 1.80 or newer (rustup)"
CARGO_ENVIRONMENT = {
    "CARGO_ENCODED_RUSTFLAGS": "",
    "RUSTC_WRAPPER": "",
    "RUSTC_WORKSPACE_WRAPPER": "",
}
"""`CARGO_ENCODED_RUSTFLAGS` outranks every other source of rustflags, and an empty value means
none; an empty wrapper turns off one configured as `build.rustc-wrapper` (sccache, for example)."""
USER_CARGO_SETTINGS = frozenset(
    {
        *("RUSTFLAGS", "RUSTC", "RUSTC_BOOTSTRAP", "RUSTDOC", "RUSTDOCFLAGS"),
        *("CARGO_ENCODED_RUSTDOCFLAGS", "CARGO_INCREMENTAL"),
    }
)
USER_CARGO_PREFIXES = (
    *("CARGO_BUILD_", "CARGO_PROFILE_", "CARGO_UNSTABLE_"),
    *("CARGO_TARGET_", "CARGO_TERM_"),
)
"""Variables of the user's environment that would change where or how the build compiles: the
compiler, the flags, the linker, runner and flags of any target (`CARGO_TARGET_<triple>_LINKER`,
and `CARGO_TARGET_DIR`), or how Cargo prints; the build leaves them out and sets its own target
directory. `PATH`, the proxy variables, `CARGO_HOME` and the rustup variables stay."""
BUILD_STEP = "cargo build"
VERSION_STEP = "rustc -vV"
_HOST_PREFIX = "host: "
_RELEASE_PREFIX = "release: "


@dataclass(frozen=True, slots=True)
class CargoOutcome:
    exit_code: int
    stdout: str
    stderr: str


class CargoToolchain(Protocol):
    """The `cargo` and `rustc` operations the Rust runner needs; tests substitute a fake."""

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CargoOutcome:
        """`cargo build <arguments>` in `cwd` with `environment` added to the pinned settings and
        to what the CLI lets user code inherit.

        Raises RunnerStartError when `cargo` cannot be started at all.
        """
        ...

    def host(self, cwd: Path) -> str:
        """The target triple of the `rustc` that `cargo` uses in `cwd`, such as
        `aarch64-apple-darwin`. Raises RunnerStartError when it cannot be found."""
        ...

    def release(self, cwd: Path) -> str:
        """The version of that `rustc`, such as `1.92.0`. Raises RunnerStartError when it cannot
        be found."""
        ...


class SubprocessCargo:
    """`CargoToolchain` backed by the commands on PATH, stopped when one outlives
    `timeout_seconds` (docs/specs/runners.md#build-timeouts)."""

    def __init__(self, timeout_seconds: float = DEFAULT_BUILD_TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CargoOutcome:
        command = [CARGO, "build", *arguments]
        inherited = inherited_environment()
        completed = self._run(BUILD_STEP, command, cwd, build_environment(inherited, environment))
        return CargoOutcome(
            completed.returncode,
            completed.stdout.decode("utf-8", errors="replace"),
            completed.stderr.decode("utf-8", errors="replace"),
        )

    def host(self, cwd: Path) -> str:
        return self._rustc_field(cwd, _HOST_PREFIX, "the host target")

    def release(self, cwd: Path) -> str:
        return self._rustc_field(cwd, _RELEASE_PREFIX, "its release")

    def _rustc_field(self, cwd: Path, prefix: str, what: str) -> str:
        """A line of `rustc -vV`, such as `host: aarch64-apple-darwin`, without its name."""
        command = [RUSTC, "-vV"]
        inherited = inherited_environment()
        completed = self._run(VERSION_STEP, command, cwd, build_environment(inherited, {}))
        return _field(completed, prefix, what)

    def _run(
        self, step: str, command: list[str], cwd: Path, environment: dict[str, str]
    ) -> "subprocess.CompletedProcess[bytes]":
        try:
            return BoundedProcess(step, self._timeout_seconds).run(command, cwd, environment)
        except FileNotFoundError:
            raise RunnerStartError(MISSING_CARGO) from None
        except OSError as error:
            raise RunnerStartError(f"cannot run {command[0]}: {error.strerror or error}") from error


def _field(completed: "subprocess.CompletedProcess[bytes]", prefix: str, what: str) -> str:
    text = completed.stdout.decode("utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    stderr = completed.stderr.decode("utf-8", errors="replace").splitlines()
    raise RunnerStartError(f"rustc -vV did not name {what}", stderr[-5:])


def build_environment(inherited: Mapping[str, str], build: Mapping[str, str]) -> dict[str, str]:
    """The process environment of a build: `inherited` without the user's build settings, then
    the pinned settings, then `build`'s."""
    kept = {
        name: value
        for name, value in inherited.items()
        if name not in USER_CARGO_SETTINGS and not name.startswith(USER_CARGO_PREFIXES)
    }
    return {**kept, **CARGO_ENVIRONMENT, **build}
