"""The Go `LanguageRunner` (docs/specs/runners.md#go-build-details).

`prepare` generates the build in `.cs/build/go` (a module joined to the workspace's `go/` module
and the runner runtime by a `go.work`), compiles one runner binary for the problem with
`go build -json`, and launches a copy of it that belongs to this run.

Compile errors in the user's or a reference file are a build failure (exit 2). Errors only in a
generated registration file mean the package does not define the expected symbol: the build is
repeated without that registration, and the runner reports a `load_error` for the target with the
compiler's message. Errors only in a generated thunk file mean a method does not have the declared
signature: the build is repeated with that file empty, and the runner, which checks signatures
through reflection, reports the mismatch.

Two `cstudy` processes may build the same problem at once (a watcher and a verify), so the
generation and the build hold an exclusive lock, and each run launches its own copy of the binary,
which no other build overwrites and which `RunnerProcess` removes when the run ends.

`cstudy test --debug` builds a binary of its own without optimizations or inlining and starts it
under a headless Delve, which holds it until the IDE attaches and continues it.
"""

import re
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
from coding_study.adapters.languages.go.build_files import (
    REGISTRATION_FILE,
    THUNK_FILE,
    VENDORED_MODULES,
    Diagnostic,
    GoPackage,
    ThunkFile,
    build_diagnostics,
    main_source,
    output_text,
    overlay_document,
    package_clause,
    registration_source,
    thunk_source,
    vendored_path,
)
from coding_study.adapters.languages.go.toolchain import GoToolchain
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    DebugLaunch,
    DebugServers,
    Prepared,
    PrepareResult,
    ProgressNotice,
    References,
    ReferenceSource,
    RunnerLaunch,
    UserCode,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import ContentError, ContentIssue, RunnerStartError
from coding_study.domain.layout import (
    BUILD_DIRECTORY,
    COMPILED_REFERENCE_PREFIX,
    COMPILED_USER_TARGET,
    GO_PROJECT,
    USER_PACKAGE,
    reference_build_path,
    snake_case,
    stub_path,
)
from coding_study.domain.naming import NameRole, constructor_name, member_name
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from coding_study.domain.signature import ClassSignature, FunctionSignature

GO_VERSION = "1.24"
"""The `go` line of the generated module and workspace; `go build -json` needs Go 1.24."""
RUNNER_MODULE = "cstudy"
RUNNER_DIRECTORY = "go"
"""The runner module inside the runners directory."""
BUILD_PROJECT = f"{BUILD_DIRECTORY}/go"
BUILD_MODULE = "csbuild"
DEFAULT_WORKSPACE_MODULE = "workspace"
MODULE_FILE = "go.mod"
WORK_FILE = "go.work"
LOCK_FILE = ".cstudy.lock"
WARM_MARKER = ".warm"
"""Written after the first successful build: the standard library and the runner are cached."""
DEBUG_WARM_MARKER = ".warm-debug"
"""The same for builds without optimizations, which compile the standard library again."""
COLD_NOTICE = "compiling the Go runner and standard library (first run)"
DEBUG_COLD_NOTICE = "compiling the Go runner and standard library for debugging (first debug run)"
DEBUG_GCFLAGS = "-gcflags=all=-N -l"
"""No optimizations and no inlining, so every line and variable of the user's code is there."""
DEBUG_BINARIES = "debug"
"""The binaries of debug builds, apart from the optimized ones of the same problem."""
DELVE_READY_MARKER = "API server listening at:"
"""What a headless Delve prints to standard output once it listens."""
WARM_BUILD_NOTE = "go, warm"
COLD_BUILD_NOTE = "go, cold"
MAX_DIAGNOSTIC_LINES = 40
OUTPUT_TAIL_LINES = 20
BUILD_PASSES = 2
"""The second pass leaves out the registrations and thunks that did not compile; a registration
holds one symbol, and a thunk file one class."""
_MODULE_LINE = re.compile(r"^module\s+(\S+)", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class _Build:
    """One runner binary: which packages it links and where its files go."""

    scope: str
    """`test`, `verify` or `bench`: each keeps its own main package and binary."""
    meta: ProblemMeta
    user: bool
    sources: tuple[ReferenceSource, ...]
    debug: bool = False
    """Without optimizations or inlining, for `cstudy test --debug`."""

    @property
    def binaries(self) -> str:
        return DEBUG_BINARIES if self.debug else self.scope


class GoRunner:
    """`LanguageRunner` for Go."""

    def __init__(
        self, context: LanguageContext, toolchain: GoToolchain, debug_servers: DebugServers
    ) -> None:
        self._root = context.workspace.resolve()
        self._runners = context.runners.resolve() / RUNNER_DIRECTORY
        self._project = self._root / GO_PROJECT
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
        """Delve starts the runner binary and holds it until the IDE attaches and continues it;
        the arguments `RunnerProcess` appends go to the runner, after `--`."""
        delve = require_installed(self._debug_servers.delve(), Language.GO)
        require_free_port(session)
        result = self._prepare(_Build("test", meta, True, (), debug=True), notify)
        if isinstance(result, BuildFailed):
            return result
        launch = result.launch
        command = (
            str(delve),
            "exec",
            "--headless",
            f"--listen={session.address}",
            "--api-version=2",
            *launch.command,
            "--",
        )
        debug = DebugLaunch(session, notify, ready_marker=DELVE_READY_MARKER)
        return replace(result, launch=replace(launch, command=command, debug=debug))

    def _prepare(self, build: _Build, notify: ProgressNotice) -> PrepareResult:
        module = self._workspace_module()
        warm_marker = self._build_directory / (DEBUG_WARM_MARKER if build.debug else WARM_MARKER)
        with exclusive_lock(self._build_directory / LOCK_FILE):
            warm = warm_marker.is_file()
            if not warm:
                notify(DEBUG_COLD_NOTICE if build.debug else COLD_NOTICE)
            self._write_module_files()
            packages = self._packages(build, module)
            result = self._compile(build, packages)
            if isinstance(result, BuildFailed):
                return result
            warm_marker.touch()
            binary = private_copy(result, self._build_directory)
        launch = RunnerLaunch(
            (str(binary),),
            self._build_directory,
            HELLO_TIMEOUT_MS[Language.GO],
            scratch=binary.parent,
        )
        return Prepared(launch, WARM_BUILD_NOTE if warm else COLD_BUILD_NOTE)

    def _workspace_module(self) -> str:
        module_file = self._project / MODULE_FILE
        try:
            text = module_file.read_text(encoding="utf-8")
        except OSError:
            message = f"{GO_PROJECT}/{MODULE_FILE} is missing; run `cstudy doctor --fix`"
            raise RunnerStartError(message) from None
        match = _MODULE_LINE.search(text)
        return match.group(1) if match else DEFAULT_WORKSPACE_MODULE

    def _write_module_files(self) -> None:
        """The build module requires the runner and the vendored modules, which references
        import; the `go.work` replaces them with the runner runtime and its copies."""
        project = relative(self._project, self._build_directory)
        runners = relative(self._runners, self._build_directory)
        vendored = VENDORED_MODULES.items()
        requires = "".join(f"\t{module} {version}\n" for module, version in vendored)
        replaces = "".join(
            f"replace {module} => {runners}/{vendored_path(module)}\n" for module, _ in vendored
        )
        write_if_changed(
            self._build_directory / MODULE_FILE,
            f"module {BUILD_MODULE}\n\ngo {GO_VERSION}\n\n"
            f"require (\n\t{RUNNER_MODULE} v0.0.0\n{requires})\n",
        )
        write_if_changed(
            self._build_directory / WORK_FILE,
            f"go {GO_VERSION}\n\nuse (\n\t.\n\t{project}\n)\n\n"
            f"replace {RUNNER_MODULE} => {runners}\n{replaces}",
        )

    def _packages(self, build: _Build, module: str) -> list[GoPackage]:
        meta = build.meta
        symbol = _registered_symbol(meta)
        packages: list[GoPackage] = []
        if build.user:
            source = self._root / stub_path(meta, Language.GO)
            packages.append(
                GoPackage(
                    COMPILED_USER_TARGET,
                    f"{module}/{USER_PACKAGE}/{meta.snake_slug}",
                    package_clause(_read(source), meta.snake_slug),
                    symbol,
                    self._generated(meta) / "user_targets.go",
                    _thunk_file(meta, self._generated(meta) / THUNK_FILE),
                )
            )
        for source in build.sources:
            packages.append(self._reference(meta, source, symbol))
        return packages

    def _reference(self, meta: ProblemMeta, source: ReferenceSource, symbol: str) -> GoPackage:
        """Copies the reference unchanged: it declares `package <snake_slug>` like the stub."""
        if not source.path.is_file():
            raise ContentError([ContentIssue(str(source.path), "", "reference file not found")])
        text = source.path.read_text(encoding="utf-8")
        target = self._root / reference_build_path(meta, source.approach_id, Language.GO)
        write_if_changed(target, text)
        approach = snake_case(source.approach_id)
        return GoPackage(
            f"{COMPILED_REFERENCE_PREFIX}/{source.approach_id}",
            f"{BUILD_MODULE}/{COMPILED_REFERENCE_PREFIX}/{meta.snake_slug}/{approach}",
            package_clause(text, meta.snake_slug),
            symbol,
            target.parent / REGISTRATION_FILE,
            _thunk_file(meta, target.parent / THUNK_FILE),
        )

    def _compile(self, build: _Build, packages: list[GoPackage]) -> "Path | BuildFailed":
        """The built binary, after a second pass without the registrations and thunks that did
        not compile; BuildFailed for errors in user code (and reference code, in verify)."""
        unavailable: dict[str, str] = {}
        without_thunks: set[str] = set()
        for _ in range(BUILD_PASSES):
            arguments = self._generate(build, packages, unavailable, without_thunks)
            outcome = self._toolchain.build(
                arguments, self._build_directory, {"GOWORK": str(self._build_directory / WORK_FILE)}
            )
            if outcome.exit_code == 0:
                return self._binary(build)
            diagnostics = build_diagnostics(outcome.stdout, outcome.stderr, self._build_directory)
            if not diagnostics:
                tail = output_text(outcome.stdout, outcome.stderr)[-OUTPUT_TAIL_LINES:]
                raise RunnerStartError(f"go build failed with exit code {outcome.exit_code}", tail)
            registrations = {package.registration.resolve(): package for package in packages}
            thunks = {
                package.thunks.path.resolve(): package for package in packages if package.thunks
            }
            source_errors = [d for d in diagnostics if d.path not in {*registrations, *thunks}]
            if source_errors:
                return self._build_failure(build, source_errors)
            for diagnostic in diagnostics:
                if diagnostic.path in thunks:
                    without_thunks.add(thunks[diagnostic.path].target_id)
                else:
                    unavailable.setdefault(
                        registrations[diagnostic.path].target_id, diagnostic.message
                    )
        raise RunnerStartError("the generated Go registration and thunk files do not compile")

    def _generate(
        self,
        build: _Build,
        packages: list[GoPackage],
        unavailable: dict[str, str],
        without_thunks: set[str],
    ) -> list[str]:
        """Writes the registrations, thunks, overlay and main package; returns the build's
        arguments."""
        overlay: dict[Path, Path] = {}
        virtual = (self._root / stub_path(build.meta, Language.GO)).parent
        for package in packages:
            source = registration_source(package, package.target_id not in unavailable)
            write_if_changed(package.registration, source)
            if package.target_id == COMPILED_USER_TARGET:
                overlay[virtual / REGISTRATION_FILE] = package.registration
            if package.thunks is not None:
                offered = package.target_id not in without_thunks
                write_if_changed(
                    package.thunks.path, thunk_source(package.thunks, package.package, offered)
                )
                if package.target_id == COMPILED_USER_TARGET:
                    overlay[virtual / THUNK_FILE] = package.thunks.path
        main = self._build_directory / "cmd" / build.scope / build.meta.snake_slug / "main.go"
        write_if_changed(main, main_source(packages, unavailable))
        arguments = ["-json", *([DEBUG_GCFLAGS] if build.debug else [])]
        if overlay:
            overlay_file = self._generated(build.meta) / "overlay.json"
            write_if_changed(overlay_file, overlay_document(overlay))
            arguments.append(f"-overlay={overlay_file}")
        package_path = f"./{main.parent.relative_to(self._build_directory).as_posix()}"
        return [*arguments, "-o", str(self._binary(build)), package_path]

    def _build_failure(self, build: _Build, diagnostics: list[Diagnostic]) -> BuildFailed:
        """Errors in reference code are content errors where only the references matter."""
        references = self._build_directory / "ref"
        in_references = [d for d in diagnostics if d.path.is_relative_to(references)]
        outside = [
            d
            for d in diagnostics
            if not d.path.is_relative_to(self._project) and d not in in_references
        ]
        if outside:
            lines = [line for d in outside for line in d.shown(str(d.path))]
            raise RunnerStartError("go build failed", lines[:OUTPUT_TAIL_LINES])
        if in_references and build.scope == "bench":
            issues = [
                ContentIssue(self._shown_path(d.path), d.position, d.message) for d in in_references
            ]
            raise ContentError(issues)
        lines = [line for d in diagnostics for line in d.shown(self._shown_path(d.path))]
        return BuildFailed(tuple(lines[:MAX_DIAGNOSTIC_LINES]))

    def _shown_path(self, path: Path) -> str:
        if path.is_relative_to(self._root):
            return path.relative_to(self._root).as_posix()
        return str(path)

    def _generated(self, meta: ProblemMeta) -> Path:
        return self._build_directory / "gen" / meta.snake_slug

    def _binary(self, build: _Build) -> Path:
        return self._build_directory / "bin" / build.binaries / build.meta.snake_slug


def _registered_symbol(meta: ProblemMeta) -> str:
    """The function, or the constructor of a class kind, that the registration exposes."""
    signature = meta.signature
    if isinstance(signature, FunctionSignature):
        return member_name(signature.name, Language.GO, NameRole.FUNCTION)
    constructor = constructor_name(signature.name, Language.GO)
    assert constructor is not None
    return constructor


def _thunk_file(meta: ProblemMeta, path: Path) -> ThunkFile | None:
    """The thunks of a design or progressive class. A concurrent class is called by stress
    workers, which keep reflection, and has no bench."""
    signature = meta.signature
    if isinstance(signature, ClassSignature) and meta.kind is not ProblemKind.CONCURRENT:
        return ThunkFile(path, signature)
    return None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
