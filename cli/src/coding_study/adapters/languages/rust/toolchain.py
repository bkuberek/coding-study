"""Running `cargo` and `rustc` for the Rust runner's build
(docs/specs/runners.md#rust-build-details).

The user's Cargo setup must neither break nor redirect a build: the build pins the target
directory, the target triple, the release profile's semantics, and runs without rustflags or a
`rustc` wrapper, whatever the environment or a `config.toml` says.
"""

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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
USER_CARGO_SETTINGS = frozenset({"RUSTFLAGS", "CARGO_TARGET_DIR"})
USER_CARGO_PREFIXES = ("CARGO_BUILD_", "CARGO_PROFILE_")
"""Variables of the user's environment that would change where or how the build compiles; the
build leaves them out and sets its own target directory."""
_HOST_PREFIX = "host: "


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
        """`cargo build <arguments>` in `cwd` with `environment` added to the pinned settings.

        Raises RunnerStartError when `cargo` cannot be started at all.
        """
        ...

    def host(self, cwd: Path) -> str:
        """The target triple of the `rustc` that `cargo` uses in `cwd`, such as
        `aarch64-apple-darwin`. Raises RunnerStartError when it cannot be found."""
        ...


class SubprocessCargo:
    """`CargoToolchain` backed by the commands on PATH."""

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CargoOutcome:
        command = [CARGO, "build", *arguments]
        completed = _run(command, cwd, build_environment(os.environ, environment))
        return CargoOutcome(
            completed.returncode,
            completed.stdout.decode("utf-8", errors="replace"),
            completed.stderr.decode("utf-8", errors="replace"),
        )

    def host(self, cwd: Path) -> str:
        completed = _run([RUSTC, "-vV"], cwd, build_environment(os.environ, {}))
        text = completed.stdout.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line.startswith(_HOST_PREFIX):
                return line.removeprefix(_HOST_PREFIX).strip()
        stderr = completed.stderr.decode("utf-8", errors="replace").splitlines()
        raise RunnerStartError("rustc -vV did not name the host target", stderr[-5:])


def _run(
    command: list[str], cwd: Path, environment: dict[str, str]
) -> "subprocess.CompletedProcess[bytes]":
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        raise RunnerStartError(MISSING_CARGO) from None
    except OSError as error:
        raise RunnerStartError(f"cannot run {command[0]}: {error.strerror or error}") from error


def build_environment(inherited: Mapping[str, str], build: Mapping[str, str]) -> dict[str, str]:
    """The process environment of a build: `inherited` without the user's build settings, then
    the pinned settings, then `build`'s."""
    kept = {
        name: value
        for name, value in inherited.items()
        if name not in USER_CARGO_SETTINGS and not name.startswith(USER_CARGO_PREFIXES)
    }
    return {**kept, **CARGO_ENVIRONMENT, **build}
