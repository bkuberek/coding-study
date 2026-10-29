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
"""

from dataclasses import dataclass, replace
from pathlib import Path

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
    Unavailable,
    bridge_source,
)
from coding_study.adapters.languages.rust.build_files import (
    DEV,
    MANIFEST_FILE,
    VENDOR_DIRECTORY,
    CompilerError,
    compiler_errors,
    executable,
    load_error,
    output_text,
    package_manifest,
    profile_arguments,
    vendored_source_arguments,
    workspace_manifest,
    workspace_members,
)
from coding_study.adapters.languages.rust.toolchain import CargoToolchain
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    DebugLaunch,
    DebugServer,
    DebugServers,
    Prepared,
    PrepareResult,
    ProgressNotice,
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
from coding_study.domain.runs import HELLO_TIMEOUT_MS

RUNNER_DIRECTORY = "rust"
"""The runner crates inside the runners directory."""
BUILD_PROJECT = f"{BUILD_DIRECTORY}/rust"
BRIDGE_FILE = "main.rs"
TARGET_DIRECTORY = "target"
HOST_FILE = "host-target"
"""The `rustc` host triple, asked once per workspace: every build passes it as `--target`."""
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
    """`LanguageRunner` for Rust."""

    def __init__(
        self, context: LanguageContext, toolchain: CargoToolchain, debug_servers: DebugServers
    ) -> None:
        self._root = context.workspace.resolve()
        self._runtime = context.runners.resolve() / RUNNER_DIRECTORY
        self._project = self._root / RUST_PROJECT
        self._build_directory = self._root / BUILD_PROJECT
        self._toolchain = toolchain
        self._debug_servers = debug_servers

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
            targets = _without_failing(targets, bridge, errors)
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
        cached = self._build_directory / HOST_FILE
        if cached.is_file():
            host = cached.read_text(encoding="utf-8").strip()
            if host:
                return host
        self._build_directory.mkdir(parents=True, exist_ok=True)
        host = self._toolchain.host(self._build_directory)
        cached.write_text(f"{host}\n", encoding="utf-8")
        return host

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


def _without_failing(
    targets: list[BridgeTarget],
    bridge: Bridge,
    errors: tuple[CompilerError, ...],
) -> list[BridgeTarget]:
    """`targets` with each one that owns a failing bridge line marked unavailable, with the
    first of its errors; a target whose module line failed (its file is missing) loses the
    module too. A failing line that no target owns means the generator is broken."""
    failures: dict[str, Unavailable] = {}
    missing_modules: set[str] = set()
    for error in errors:
        owner = bridge.owners.get(error.line)
        if owner is None:
            shown = error.shown(str(error.path))
            raise RunnerStartError("the generated Rust bridge does not compile", shown)
        if error.line in bridge.modules:
            missing_modules.add(owner)
        target = next(target for target in targets if target.target_id == owner)
        failures.setdefault(owner, load_error(error, target.module, target.file.name))
    return [
        replace(
            target,
            unavailable=failures[target.target_id],
            with_module=target.target_id not in missing_modules,
        )
        if target.target_id in failures
        else target
        for target in targets
    ]
