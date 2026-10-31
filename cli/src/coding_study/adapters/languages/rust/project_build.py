"""The builds of a Rust project folder (docs/specs/runners.md#rust-projects).

A project is a crate of its own, and Cargo refuses a workspace member outside the workspace's
root, so each problem gets a Cargo workspace of its own, `.cs/build/rust-projects/<slug>/`, whose
only member is the harness: a package that depends on the project crate by path, under the name
`user`, and whose `main.rs` is the generated bridge. The suite builds the crate's test targets
(`-p <crate> --lib --tests --keep-going`) and the grading the harness; both use the dev profile and
share `.cs/build/rust/target`, so a grade after a suite run compiles only the harness. A private
`CARGO_HOME` keeps concurrent builds from waiting on the package-cache lock of a shared one, and
nothing is written into the project folder.

The build holds an exclusive lock on its workspace while it writes, builds and copies the binaries
it hands out, so a build by another `cstudy` process never changes them under a run.
"""

import tomllib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.languages.compiled_builds import (
    private_copies,
    relative,
    write_if_changed,
)
from coding_study.adapters.languages.rust.bridge import BridgeTarget, bridge_source
from coding_study.adapters.languages.rust.build_files import (
    DEV,
    MANIFEST_FILE,
    USER_CRATE,
    VENDOR_DIRECTORY,
    CompilerError,
    built_test_binaries,
    compiler_errors,
    executable,
    marked_unavailable,
    profile_arguments,
    project_harness_manifest,
    target_errors,
    vendored_source_arguments,
    workspace_manifest,
)
from coding_study.adapters.languages.rust.toolchain import CargoOutcome, CargoToolchain
from coding_study.application.ports import BuildFailed
from coding_study.application.project_runs import COMPILE_ERROR
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.layout import BUILD_DIRECTORY, COMPILED_USER_TARGET, snake_case
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import UserError
from coding_study.domain.signature import ClassSignature

PROJECT_BUILDS = f"{BUILD_DIRECTORY}/rust-projects"
TARGET_DIRECTORY = f"{BUILD_DIRECTORY}/rust/target"
"""Shared with the single-file builds, so the runner crates compile once per profile."""
HARNESS_DIRECTORY = "harness"
HARNESS_PREFIX = "project_"
BRIDGE_FILE = "main.rs"
PLACEHOLDER_BRIDGE = "fn main() {}\n"
"""What the harness holds before its first grading: a suite build never compiles it, but its
package must load."""
CARGO_HOME_DIRECTORY = "cargo-home"
LOCK_FILE = ".cstudy.lock"
WARM_MARKER = ".warm"
"""Written after the first successful build of the harness: the runner crates are compiled."""
SUITE_TARGETS = ("--lib", "--tests", "--keep-going")
CARGO_ERROR = "CargoError"
MAX_DIAGNOSTIC_LINES = 40
OUTPUT_TAIL_LINES = 20
BUILD_PASSES = 2
"""The second pass leaves out the user's target when its bridge code did not compile."""
_PACKAGE_TABLE = "package"
_PACKAGE_NAME = "name"


@dataclass(frozen=True, slots=True)
class RustBuildSettings:
    """What every Rust build of a workspace shares."""

    workspace: Path
    """The workspace root, resolved."""
    runtime: Path
    """The runner runtime's `rust/` directory, resolved."""
    toolchain: CargoToolchain
    host: Callable[[], str]
    """The target triple every build passes as `--target`."""


@dataclass(frozen=True, slots=True)
class SuiteTarget:
    """One test target of the project crate, as the suite build left it."""

    path: str
    """Its source root, relative to the project root: `src/lib.rs`, `tests/level_1.rs`."""
    binary: Path | None = None
    """This run's copy of its test binary; None when it did not compile."""
    error: UserError | None = None
    """Its compiler errors, when it did not compile."""


@dataclass(frozen=True, slots=True)
class BuiltTests:
    targets: tuple[SuiteTarget, ...]
    """In path order."""
    scratch: Path | None
    """The directory of this run's copies of the binaries, which the caller removes."""


class ProjectBuildError(Exception):
    """Cargo could not build the project for a reason in the folder that is not a compiler
    error: a `Cargo.toml` it cannot read, for example."""

    def __init__(self, error: UserError) -> None:
        super().__init__(error.message)
        self.error = error


class RustProjectBuild:
    """The build workspace of one problem, for the project folder at `root`."""

    def __init__(self, settings: RustBuildSettings, slug: str, root: Path) -> None:
        self._settings = settings
        self._root = root.resolve()
        self._directory = settings.workspace / PROJECT_BUILDS / slug
        self._package = f"{HARNESS_PREFIX}{snake_case(slug)}"

    @property
    def directory(self) -> Path:
        return self._directory

    @property
    def warm(self) -> bool:
        return (self._directory / WARM_MARKER).is_file()

    def harness(self, signature: ClassSignature) -> Path | BuildFailed:
        """A private copy of the harness binary, whose bridge calls the methods of `signature`;
        BuildFailed when the project's own code does not compile.

        Raises RunnerStartError when the build fails for a reason outside the project.
        """
        with exclusive_lock(self._directory / LOCK_FILE):
            try:
                crate = self._crate()
            except ProjectBuildError as error:
                return BuildFailed(_lines(error.error))
            target = BridgeTarget(COMPILED_USER_TARGET, USER_CRATE, self._root, crate=True)
            built = self._harness_binary(signature, crate, [target])
            if isinstance(built, BuildFailed):
                return built
            (self._directory / WARM_MARKER).touch()
            _, (copy,) = private_copies((built,), self._directory)
            return copy

    def tests(self, exclude: Iterable[str]) -> BuiltTests:
        """Every test target of the crate but those whose source root is in `exclude`, each with
        a private copy of its binary or its compiler errors.

        Raises ProjectBuildError for a project Cargo cannot build at all, and RunnerStartError
        for a failure outside the project.
        """
        excluded = frozenset(exclude)
        with exclusive_lock(self._directory / LOCK_FILE):
            crate = self._crate()
            self._write(crate, None)
            outcome = self._cargo(crate, SUITE_TARGETS)
            binaries = {
                path: binary
                for source, binary in built_test_binaries(outcome.stdout)
                if (path := self._shown(source)) not in excluded
            }
            if outcome.exit_code != 0 and not target_errors(outcome.stdout, self._directory):
                self._cargo_failure(outcome)
            errors = self._target_errors(outcome, excluded)
            scratch, copies = private_copies(tuple(binaries.values()), self._directory)
        built = [SuiteTarget(path, copy) for path, copy in zip(binaries, copies, strict=True)]
        failed = [
            SuiteTarget(path, error=_first_and_rest(COMPILE_ERROR, lines))
            for path, lines in errors.items()
        ]
        targets = sorted((*built, *failed), key=lambda target: target.path)
        return BuiltTests(tuple(targets), scratch)

    def _harness_binary(
        self, signature: ClassSignature, crate: str, targets: list[BridgeTarget]
    ) -> Path | BuildFailed:
        bridge_file = (self._directory / HARNESS_DIRECTORY / BRIDGE_FILE).resolve()
        for _ in range(BUILD_PASSES):
            bridge = bridge_source(signature, targets, kind=ProblemKind.PROJECT)
            self._write(crate, bridge.text)
            outcome = self._cargo(self._package, ())
            if outcome.exit_code == 0:
                return self._binary(outcome)
            errors = compiler_errors(outcome.stdout, self._directory)
            if not errors:
                return BuildFailed(self._failure_lines(outcome))
            source_errors = [error for error in errors if error.path != bridge_file]
            if source_errors:
                return BuildFailed(self._source_lines(source_errors))
            targets = marked_unavailable(targets, bridge, errors)
        raise RunnerStartError("the generated Rust bridge does not compile")

    def _crate(self) -> str:
        """The package name in the root's `Cargo.toml`, read on every build."""
        manifest = self._root / MANIFEST_FILE
        try:
            document = tomllib.loads(manifest.read_text(encoding="utf-8"))
        except OSError:
            raise ProjectBuildError(UserError(CARGO_ERROR, f"{MANIFEST_FILE} is missing")) from None
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            message = f"{MANIFEST_FILE} is not valid TOML: {error}"
            raise ProjectBuildError(UserError(CARGO_ERROR, message)) from None
        package: object = document.get(_PACKAGE_TABLE)
        fields = cast("dict[str, object]", package) if isinstance(package, dict) else {}
        name = fields.get(_PACKAGE_NAME)
        if not isinstance(name, str) or not name:
            message = f"{MANIFEST_FILE} names no package: [package] needs a name"
            raise ProjectBuildError(UserError(CARGO_ERROR, message))
        return name

    def _write(self, crate: str, bridge: str | None) -> None:
        """The workspace and the harness; without a bridge, the harness keeps the one it has."""
        harness = self._directory / HARNESS_DIRECTORY
        runtime = relative(self._settings.runtime, harness)
        root = relative(self._root, harness)
        manifest = project_harness_manifest(self._package, crate, root, runtime)
        write_if_changed(harness / MANIFEST_FILE, manifest)
        if bridge is not None:
            write_if_changed(harness / BRIDGE_FILE, bridge)
        elif not (harness / BRIDGE_FILE).is_file():
            write_if_changed(harness / BRIDGE_FILE, PLACEHOLDER_BRIDGE)
        manifest_file = self._directory / MANIFEST_FILE
        write_if_changed(manifest_file, workspace_manifest([HARNESS_DIRECTORY]))

    def _cargo(self, package: str, targets: tuple[str, ...]) -> CargoOutcome:
        settings = self._settings
        arguments = [
            *("--offline", "--profile", DEV, "--message-format=json"),
            *("--target", settings.host(), "-p", package, *targets),
            *profile_arguments(DEV),
            *vendored_source_arguments(settings.runtime / VENDOR_DIRECTORY),
        ]
        environment = {
            "CARGO_TARGET_DIR": str(settings.workspace / TARGET_DIRECTORY),
            "CARGO_HOME": str(self._directory / CARGO_HOME_DIRECTORY),
        }
        return settings.toolchain.build(arguments, self._directory, environment)

    def _binary(self, outcome: CargoOutcome) -> Path:
        built = executable(outcome.stdout, self._package)
        if built is None:
            raise RunnerStartError(f"cargo build reported no binary for {self._package}")
        return built

    def _target_errors(
        self, outcome: CargoOutcome, excluded: frozenset[str]
    ) -> dict[str, tuple[str, ...]]:
        """The diagnostic lines of each test target that did not compile, without the targets
        left out; a library's errors are reported once for its unit tests and once for itself."""
        found: dict[str, list[str]] = {}
        seen: set[tuple[str, ...]] = set()
        for source, error in target_errors(outcome.stdout, self._directory):
            path = self._shown(source)
            if path in excluded:
                continue
            if not error.path.is_relative_to(self._root):
                lines = error.shown(str(error.path))
                raise RunnerStartError("cargo build failed outside the project", lines)
            lines = error.shown(self._shown(error.path))
            if lines not in seen:
                seen.add(lines)
                found.setdefault(path, []).extend(lines)
        return {path: tuple(lines[:MAX_DIAGNOSTIC_LINES]) for path, lines in found.items()}

    def _source_lines(self, errors: list[CompilerError]) -> tuple[str, ...]:
        """Compiler errors in the project's files; any elsewhere mean the runner is broken."""
        outside = [error for error in errors if not error.path.is_relative_to(self._root)]
        if outside:
            lines = [line for error in outside for line in error.shown(str(error.path))]
            raise RunnerStartError("cargo build failed", lines[:OUTPUT_TAIL_LINES])
        lines = [line for error in errors for line in error.shown(self._shown(error.path))]
        return tuple(dict.fromkeys(lines))[:MAX_DIAGNOSTIC_LINES]

    def _failure_lines(self, outcome: CargoOutcome) -> tuple[str, ...]:
        """What Cargo said about a failure without compiler errors, when it is the project's."""
        try:
            self._cargo_failure(outcome)
        except ProjectBuildError as error:
            return _lines(error.error)
        raise AssertionError("_cargo_failure always raises")

    def _cargo_failure(self, outcome: CargoOutcome) -> None:
        """Raises ProjectBuildError when Cargo's error names the project folder (an unknown
        dependency in its `Cargo.toml`, say), else RunnerStartError."""
        lines = [line for line in outcome.stderr.splitlines() if line.strip()]
        if any(str(self._root) in line for line in lines):
            shown = [line.replace(f"{self._root}/", "") for line in lines]
            raise ProjectBuildError(_first_and_rest(CARGO_ERROR, shown[:MAX_DIAGNOSTIC_LINES]))
        message = f"cargo build failed with exit code {outcome.exit_code}"
        raise RunnerStartError(message, lines[-OUTPUT_TAIL_LINES:])

    def _shown(self, path: Path) -> str:
        """`path` relative to the project root, as reports name it."""
        resolved = path.resolve()
        if resolved.is_relative_to(self._root):
            return resolved.relative_to(self._root).as_posix()
        return str(path)


def _lines(error: UserError) -> tuple[str, ...]:
    return tuple(line for line in (error.message, *error.trace.splitlines()) if line)


def _first_and_rest(kind: str, lines: Sequence[str]) -> UserError:
    """The first line as the message, the others as the trace: the first compiler error leads."""
    first, *rest = lines or ("",)
    return UserError(kind, first, "\n".join(rest))
