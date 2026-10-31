"""The Rust `LanguageRunner` (docs/specs/runners.md#rust-build-details).

`prepare` generates the build in `.cs/build/rust`, a Cargo workspace with one harness package per
problem and scope whose `main.rs` is the generated bridge, compiles it with
`cargo build --offline --release --message-format=json`, crates.io replaced by the runtime's
vendored crates, and launches a copy of the binary that belongs to this run (`RunnerProcess`
removes it when the run ends).

Compile errors in the user's or a reference file are a build failure (exit 2). Errors only in the
bridge mean a target does not define what the signature declares: the build is repeated with
those targets left out of the bridge, and the runner reports a `load_error` for each of them
with the compiler's message in the user's terms.

`cstudy test --debug` builds with the dev profile and starts the binary under LLDB's debug server
(`debugserver` on macOS, `lldb-server gdbserver` on Linux), which holds it at its entry point
until the IDE connects with `gdb-remote` and continues it. The server prints nothing: it writes
its port to the file `--named-pipe` names once it listens.

A project problem builds in a workspace of its own (`project_build`): its grading launches the
harness binary like any runner, and its suite runs each test as a process of its own
(`project_suite`), with no runner process at all (docs/specs/runners.md#rust-projects).
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from shutil import rmtree

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.languages.compiled_builds import (
    private_copy,
    relative,
    write_if_changed,
)
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.debug_port import require_free_port
from coding_study.adapters.languages.debug_servers import require_installed
from coding_study.adapters.languages.rust.bridge import (
    Bridge,
    BridgeTarget,
    bridge_source,
)
from coding_study.adapters.languages.rust.build_files import (
    DEV,
    MANIFEST_FILE,
    VENDOR_DIRECTORY,
    CompilerError,
    compiler_errors,
    executable,
    marked_unavailable,
    output_text,
    package_manifest,
    profile_arguments,
    vendored_source_arguments,
    workspace_manifest,
    workspace_members,
)
from coding_study.adapters.languages.rust.project_build import (
    ProjectBuildError,
    RustBuildSettings,
    RustProjectBuild,
)
from coding_study.adapters.languages.rust.project_suite import (
    DebugTarget,
    LibtestProcesses,
    LibtestSuite,
    SubprocessTests,
)
from coding_study.adapters.languages.rust.toolchain import CargoToolchain
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    DebugLaunch,
    DebugServer,
    DebugServers,
    HostedSuite,
    Prepared,
    PrepareResult,
    ProgressNotice,
    ProjectGrading,
    ProjectScope,
    ProjectSuite,
    References,
    ReferenceSource,
    RunnerLaunch,
    UserCode,
)
from coding_study.domain.debugging import LLDB_SERVER, DebugSession
from coding_study.domain.errors import ContentError, ContentIssue, RunnerStartError
from coding_study.domain.layout import (
    BUILD_DIRECTORY,
    COMPILED_REFERENCE_PREFIX,
    COMPILED_USER_TARGET,
    RUST_PROJECT,
    reference_build_path,
    snake_case,
    stub_path,
)
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runner_grading import graded_signature
from coding_study.domain.runs import HELLO_TIMEOUT_MS, PROTOCOL_VERSION, RunnerInfo
from coding_study.domain.suite_runs import SuiteReport

RUNNER_DIRECTORY = "rust"
"""The runner crates inside the runners directory."""
BUILD_PROJECT = f"{BUILD_DIRECTORY}/rust"
BRIDGE_FILE = "main.rs"
TARGET_DIRECTORY = "target"
HOST_FILE = "host-target"
"""The `rustc` host triple, asked once per workspace: every build passes it as `--target`."""
RELEASE_FILE = "rustc-release"
"""The `rustc` version, asked once per workspace: a project suite's report names it."""
RUNNER_NAME = "rust"
LOCK_FILE = ".cstudy.lock"
WARM_MARKER = ".warm"
"""Written after the first successful build: the runner crates are compiled."""
DEBUG_WARM_MARKER = ".warm-debug"
"""The same for the dev profile of `cstudy test --debug`."""
USER_MODULE = "user"
REFERENCE_MODULE_PREFIX = "ref_"
COLD_NOTICE = "compiling the Rust runner (first run)"
DEBUG_COLD_NOTICE = "compiling the Rust runner for debugging (first debug run)"
READY_FILE = "debug-port"
"""In the launch's scratch directory: the debug server writes its port there once it listens."""
GDBSERVER_MODE = "gdbserver"
"""`lldb-server`'s mode for a remote debugger; `debugserver` has only that one."""
WARM_BUILD_NOTE = "rust, warm"
COLD_BUILD_NOTE = "rust, cold"
MAX_DIAGNOSTIC_LINES = 40
OUTPUT_TAIL_LINES = 20
BUILD_PASSES = 2
"""The second pass leaves out the targets whose bridge code did not compile."""


@dataclass(frozen=True, slots=True)
class _Build:
    """One runner binary: which targets it links and where its files go."""

    scope: str
    """`test`, `verify` or `bench`: each keeps its own harness package and binary."""
    meta: ProblemMeta
    user: bool
    sources: tuple[ReferenceSource, ...]
    debug: bool = False
    """With the dev profile, for `cstudy test --debug`."""

    @property
    def package(self) -> str:
        return f"{self.scope}_{self.meta.snake_slug}"

    @property
    def profile_options(self) -> tuple[str, ...]:
        return ("--profile", DEV) if self.debug else ("--release",)


class RustRunner:
    """`LanguageRunner`, `ProjectRunner` and `ProjectSuiteHost` for Rust."""

    def __init__(
        self,
        context: LanguageContext,
        toolchain: CargoToolchain,
        debug_servers: DebugServers,
        tests: LibtestProcesses | None = None,
    ) -> None:
        self._root = context.workspace.resolve()
        self._runtime = context.runners.resolve() / RUNNER_DIRECTORY
        self._project = self._root / RUST_PROJECT
        self._build_directory = self._root / BUILD_PROJECT
        self._toolchain = toolchain
        self._debug_servers = debug_servers
        self._tests = tests or SubprocessTests()

    def prepare_project(
        self, scope: ProjectScope, notify: ProgressNotice
    ) -> RunnerLaunch | BuildFailed:
        """The harness of a grading, built from the graded levels' signature; BuildFailed when
        the project's own code does not compile. A suite never comes here: `run_project_suite`
        runs it.

        Raises RunnerStartError when the build fails outside the project.
        """
        match scope:
            case ProjectGrading(meta=ProblemMeta() as meta, level=int() as level):
                return self._prepare_grading(scope.root, meta, level, notify)
            case ProjectGrading():
                raise ValueError("a Rust grading builds its bridge from the graded problem")
            case ProjectSuite():
                raise ValueError("a Rust project's suite runs through run_project_suite")

    def run_project_suite(self, suite: HostedSuite, notify: ProgressNotice) -> SuiteReport:
        """Builds every test target of the project, then runs each test as a process of its own
        (docs/specs/runners.md#rust-projects). A debug server is looked up, and the debug port
        checked, before anything is built.

        Raises RunnerStartError when the toolchain cannot build or run the suite.
        """
        job = suite.job
        debugging = None if suite.debug is None else self._debug_target(suite.debug, notify)
        runner = RunnerInfo(RUNNER_NAME, PROTOCOL_VERSION, self._release())
        build = RustProjectBuild(self._settings(), suite.slug, Path(job.root))
        try:
            built = build.tests(job.exclude)
        except ProjectBuildError as error:
            return SuiteReport(runner, load_error=error.error)
        try:
            libtest = LibtestSuite(self._tests, job, suite.listener)
            if debugging is None:
                return SuiteReport(runner, libtest.run(built))
            tests, stopped_early = libtest.debug(built, debugging)
            return SuiteReport(runner, tests, stopped_early=stopped_early)
        finally:
            if built.scratch is not None:
                rmtree(built.scratch, ignore_errors=True)

    def _prepare_grading(
        self, root: Path, meta: ProblemMeta, level: int, notify: ProgressNotice
    ) -> RunnerLaunch | BuildFailed:
        build = RustProjectBuild(self._settings(), meta.slug, root)
        if not build.warm:
            notify(COLD_NOTICE)
        binary = build.harness(graded_signature(meta.signature, level))
        if isinstance(binary, BuildFailed):
            return binary
        timeout = HELLO_TIMEOUT_MS[Language.RUST]
        return RunnerLaunch((str(binary),), root, timeout, scratch=binary.parent)

    def _debug_target(self, session: DebugSession, notify: ProgressNotice) -> DebugTarget:
        server = self._debug_servers.lldb_server()
        path = require_installed(server, Language.RUST)
        require_free_port(session)
        return DebugTarget(session, server.name, path, notify)

    def _settings(self) -> RustBuildSettings:
        return RustBuildSettings(self._root, self._runtime, self._toolchain, self._host)

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        match scope:
            case UserCode(debug=DebugSession() as session):
                return self._prepare_debug(scope.meta, session, notify)
            case UserCode():
                build = _Build("test", scope.meta, True, ())
            case References():
                build = _Build("verify", scope.meta, False, scope.sources)
            case BenchCode():
                build = _Build("bench", scope.meta, not scope.references_only, scope.sources)
        return self._prepare(build, notify)

    def _prepare_debug(
        self, meta: ProblemMeta, session: DebugSession, notify: ProgressNotice
    ) -> PrepareResult:
        """The debug server starts the runner binary and holds it until the IDE continues it;
        the arguments `RunnerProcess` appends go to the runner, after `--`."""
        server = self._debug_servers.lldb_server()
        path = require_installed(server, Language.RUST)
        require_free_port(session)
        result = self._prepare(_Build("test", meta, True, (), debug=True), notify)
        if isinstance(result, BuildFailed):
            return result
        launch = result.launch
        assert launch.scratch is not None
        ready_file = launch.scratch / READY_FILE
        command = (
            *_server_command(server, path),
            "--named-pipe",
            str(ready_file),
            session.address,
            "--",
            *launch.command,
        )
        debug = DebugLaunch(session, notify, ready_file=ready_file)
        return replace(result, launch=replace(launch, command=command, debug=debug))

    def _prepare(self, build: _Build, notify: ProgressNotice) -> PrepareResult:
        warm_marker = self._build_directory / (DEBUG_WARM_MARKER if build.debug else WARM_MARKER)
        with exclusive_lock(self._build_directory / LOCK_FILE):
            warm = warm_marker.is_file()
            if not warm:
                notify(DEBUG_COLD_NOTICE if build.debug else COLD_NOTICE)
            targets = self._targets(build)
            result = self._compile(build, targets)
            if isinstance(result, BuildFailed):
                return result
            warm_marker.touch()
            binary = private_copy(result, self._build_directory)
        launch = RunnerLaunch(
            (str(binary),),
            self._build_directory,
            HELLO_TIMEOUT_MS[Language.RUST],
            scratch=binary.parent,
        )
        return Prepared(launch, WARM_BUILD_NOTE if warm else COLD_BUILD_NOTE)

    def _targets(self, build: _Build) -> list[BridgeTarget]:
        meta = build.meta
        targets: list[BridgeTarget] = []
        if build.user:
            user_file = self._root / stub_path(meta, Language.RUST)
            targets.append(BridgeTarget(COMPILED_USER_TARGET, USER_MODULE, user_file))
        for source in build.sources:
            targets.append(self._reference(meta, source))
        return targets

    def _reference(self, meta: ProblemMeta, source: ReferenceSource) -> BridgeTarget:
        """Copies the reference unchanged into `.cs/build/rust/ref/<snake_slug>/`."""
        if not source.path.is_file():
            raise ContentError([ContentIssue(str(source.path), "", "reference file not found")])
        target = self._root / reference_build_path(meta, source.approach_id, Language.RUST)
        write_if_changed(target, source.path.read_text(encoding="utf-8"))
        module = f"{REFERENCE_MODULE_PREFIX}{snake_case(source.approach_id)}"
        return BridgeTarget(f"{COMPILED_REFERENCE_PREFIX}/{source.approach_id}", module, target)

    def _compile(self, build: _Build, targets: list[BridgeTarget]) -> "Path | BuildFailed":
        """The built binary, after a second pass without the targets whose bridge code did not
        compile; BuildFailed for errors in user code (and reference code, in verify)."""
        package = self._build_directory / build.scope / build.meta.snake_slug
        arguments = [
            *("--offline", *build.profile_options, "--message-format=json"),
            *("--target", self._host(), "-p", build.package),
            *(profile_arguments(DEV) if build.debug else profile_arguments()),
            *vendored_source_arguments(self._runtime / VENDOR_DIRECTORY),
        ]
        environment = {"CARGO_TARGET_DIR": str(self._build_directory / TARGET_DIRECTORY)}
        for _ in range(BUILD_PASSES):
            bridge = bridge_source(build.meta.signature, targets, kind=build.meta.kind)
            self._write_package(build, package, bridge)
            outcome = self._toolchain.build(arguments, self._build_directory, environment)
            if outcome.exit_code == 0:
                return self._binary(build, outcome.stdout)
            errors = compiler_errors(outcome.stdout, self._build_directory)
            if not errors:
                tail = output_text(outcome.stdout, outcome.stderr)[-OUTPUT_TAIL_LINES:]
                raise RunnerStartError(
                    f"cargo build failed with exit code {outcome.exit_code}", tail
                )
            bridge_file = (package / BRIDGE_FILE).resolve()
            source_errors = [error for error in errors if error.path != bridge_file]
            if source_errors:
                return self._build_failure(build, source_errors)
            targets = marked_unavailable(targets, bridge, errors)
        raise RunnerStartError("the generated Rust bridge does not compile")

    def _write_package(self, build: _Build, package: Path, bridge: Bridge) -> None:
        """The harness package, then the workspace manifest that lists it."""
        runtime = relative(self._runtime, package)
        write_if_changed(package / MANIFEST_FILE, package_manifest(build.package, runtime))
        write_if_changed(package / BRIDGE_FILE, bridge.text)
        members = workspace_members(self._build_directory)
        write_if_changed(self._build_directory / MANIFEST_FILE, workspace_manifest(members))

    def _binary(self, build: _Build, stdout: str) -> Path:
        built = executable(stdout, build.package)
        if built is None:
            raise RunnerStartError(f"cargo build reported no binary for {build.package}")
        return built

    def _host(self) -> str:
        """The host triple, from `rustc -vV` once, then from the build directory."""
        return self._cached(HOST_FILE, self._toolchain.host)

    def _release(self) -> str:
        """The `rustc` version, from `rustc -vV` once, then from the build directory."""
        return self._cached(RELEASE_FILE, self._toolchain.release)

    def _cached(self, name: str, ask: Callable[[Path], str]) -> str:
        cached = self._build_directory / name
        if cached.is_file():
            value = cached.read_text(encoding="utf-8").strip()
            if value:
                return value
        self._build_directory.mkdir(parents=True, exist_ok=True)
        value = ask(self._build_directory)
        cached.write_text(f"{value}\n", encoding="utf-8")
        return value

    def _build_failure(self, build: _Build, errors: list[CompilerError]) -> BuildFailed:
        """Errors in reference code are content errors where only the references matter;
        errors anywhere else but the practice project mean the runner itself is broken."""
        references = self._build_directory / "ref"
        in_references = [error for error in errors if error.path.is_relative_to(references)]
        outside = [
            error
            for error in errors
            if not error.path.is_relative_to(self._project) and error not in in_references
        ]
        if outside:
            lines = [line for error in outside for line in error.shown(str(error.path))]
            raise RunnerStartError("cargo build failed", lines[:OUTPUT_TAIL_LINES])
        if in_references and build.scope == "bench":
            issues = [
                ContentIssue(
                    self._shown_path(error.path), f"{error.line}:{error.column}", error.message
                )
                for error in in_references
            ]
            raise ContentError(issues)
        lines = [line for error in errors for line in error.shown(self._shown_path(error.path))]
        return BuildFailed(tuple(lines[:MAX_DIAGNOSTIC_LINES]))

    def _shown_path(self, path: Path) -> str:
        if path.is_relative_to(self._root):
            return path.relative_to(self._root).as_posix()
        return str(path)


def _server_command(server: DebugServer, path: Path) -> tuple[str, ...]:
    return (str(path), GDBSERVER_MODE) if server.name == LLDB_SERVER else (str(path),)
