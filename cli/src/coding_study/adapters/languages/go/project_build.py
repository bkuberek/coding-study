"""The binaries of a Go project's jobs (docs/specs/runners.md#go-project-jobs).

Each project root, the user's folder or a reference's build copy, gets a `go.work` of its own in
`.cs/build/go/project/<root>/` that joins the build module and the root and replaces the runner
module and the vendored modules with the runtime's copies, so a root at any depth builds. The
grading binary links the entry's package with a registration and thunks that enter it through
`go build -overlay`, as a practice file's do, with the thunks of the graded levels' methods only.
A project that does not compile gets a binary that reports the compiler's errors as a load error.
The suite binary is the runner with no target: it runs `go test` in the root, whose environment
the launch sets.
"""

import json
import posixpath
import re
from dataclasses import dataclass, replace
from pathlib import Path

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.languages.compiled_builds import private_copy, relative, write_if_changed
from coding_study.adapters.languages.debug_port import require_free_port
from coding_study.adapters.languages.debug_servers import require_installed
from coding_study.adapters.languages.go.build_files import (
    BUILD_PASSES,
    BUILD_PROJECT,
    COLD_NOTICE,
    DELVE_READY_MARKER,
    GENERATED_HEADER,
    GO_VERSION,
    LOCK_FILE,
    MAX_DIAGNOSTIC_LINES,
    MODULE_FILE,
    OUTPUT_TAIL_LINES,
    REGISTRATION_FILE,
    RUNNER_MODULE,
    RUNNER_PACKAGE,
    THUNK_FILE,
    VENDORED_MODULES,
    WARM_MARKER,
    WORK_FILE,
    Diagnostic,
    GoPackage,
    ThunkFile,
    build_diagnostics,
    build_module_source,
    main_source,
    output_text,
    overlay_document,
    package_clause,
    registration_source,
    thunk_source,
    vendored_path,
)
from coding_study.adapters.languages.go.toolchain import GO_ENVIRONMENT, GoOutcome, GoToolchain
from coding_study.application.ports import (
    DebugLaunch,
    DebugServers,
    ProgressNotice,
    ProjectGrading,
    ProjectSuite,
    RunnerLaunch,
)
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.layout import COMPILED_USER_TARGET
from coding_study.domain.naming import constructor_name
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runner_grading import graded_signature
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from coding_study.domain.workspace_projects import GoModuleFile, go_module_file

PROJECT_BUILDS = "project"
"""Below the build directory: one directory per project root, mirroring its path."""
PROJECT_BINARIES = "project"
SUITE_BINARY = "cs_go_suite"
SUITE_SCOPE = "suite"
SUITE_WARM_MARKER = ".warm-suite"
"""Written after the first suite build, which also compiles the test framework."""
TEST_FRAMEWORK_PACKAGES = ("testing", "testing/internal/testdeps")
"""What every test binary links beyond the runner's packages; compiled once, before the first
suite, so that a cold build cache does not stall `go test` under the hang guard."""
OVERLAY_FILE = "overlay.json"
OUTSIDE_WORKSPACE = "outside"
"""The directory of the builds of roots outside the workspace, by their absolute path."""
DEBUG_LISTEN = "CSTUDY_GO_DEBUG_LISTEN"
DEBUG_DELVE = "CSTUDY_GO_DELVE"
DEBUG_PACKAGE = "CSTUDY_GO_DEBUG_PACKAGE"
_GO_VERSION_PARTS = re.compile(r"\d+")
_UNSET = ""
"""The go command reads an empty GOOS or GOARCH as unset: this machine's platform."""


@dataclass(frozen=True, slots=True)
class _Root:
    """One project root and its build files."""

    path: Path
    """Resolved."""
    directory: Path
    """`.cs/build/go/project/<root>/`: its `go.work`, registration, thunks and overlay."""

    @property
    def work_file(self) -> Path:
        return self.directory / WORK_FILE


class GoProjectBuilds:
    """`ProjectRunner.prepare_project` for Go."""

    def __init__(
        self,
        workspace: Path,
        runners: Path,
        toolchain: GoToolchain,
        debug_servers: DebugServers,
    ) -> None:
        self._workspace = workspace
        self._runners = runners
        self._build_directory = workspace / BUILD_PROJECT
        self._toolchain = toolchain
        self._debug_servers = debug_servers

    def grading(self, scope: ProjectGrading, notify: ProgressNotice) -> RunnerLaunch:
        """Raises RunnerStartError when the project's module cannot be read or the build fails
        outside the project, and ValueError for a scope without a project problem."""
        meta, level = scope.meta, scope.level
        if meta is None or meta.project is None or level is None:
            raise ValueError("a Go project is graded with its problem and level")
        root = self._root(scope.root)
        module = self._module(root)
        with exclusive_lock(self._build_directory / LOCK_FILE):
            self._first_build(WARM_MARKER, notify)
            self._write_work_file(root, module.go)
            binary = _GradingBuild(self, root, meta, level, module.module or meta.slug).build()
            (self._build_directory / WARM_MARKER).touch()
            copy = private_copy(binary, self._build_directory)
        return RunnerLaunch(
            (str(copy),), scope.root, HELLO_TIMEOUT_MS[Language.GO], scratch=copy.parent
        )

    def suite(self, scope: ProjectSuite, notify: ProgressNotice) -> RunnerLaunch:
        """Raises RunnerStartError when Delve is missing for a debug run, its port is taken, or
        the suite runner does not build."""
        debug_environment: dict[str, str] = {}
        if scope.debug is not None:
            delve = require_installed(self._debug_servers.delve(), Language.GO)
            require_free_port(scope.debug)
            debug_environment = {DEBUG_LISTEN: scope.debug.address, DEBUG_DELVE: str(delve)}
            if scope.meta is not None and scope.meta.project is not None:
                debug_environment[DEBUG_PACKAGE] = scope.meta.project.tests
        root = self._root(scope.root)
        with exclusive_lock(self._build_directory / LOCK_FILE):
            cold = self._first_build(SUITE_WARM_MARKER, notify)
            self._write_work_file(root, self._go_line(root))
            binary = self._build_suite(root, cold)
            copy = private_copy(binary, self._build_directory)
        environment = {
            **GO_ENVIRONMENT,
            "GOWORK": str(root.work_file),
            "GOOS": _UNSET,
            "GOARCH": _UNSET,
            **debug_environment,
        }
        launch = RunnerLaunch(
            (str(copy),),
            scope.root,
            HELLO_TIMEOUT_MS[Language.GO],
            scratch=copy.parent,
            environment=environment,
        )
        if scope.debug is None:
            return launch
        return replace(launch, debug=DebugLaunch(scope.debug, notify, DELVE_READY_MARKER))

    def build(self, arguments: list[str], root: _Root) -> GoOutcome:
        """`go build <arguments>` in the build directory, against the root's `go.work`."""
        return self._toolchain.build(
            arguments, self._build_directory, {"GOWORK": str(root.work_file)}
        )

    @property
    def build_directory(self) -> Path:
        return self._build_directory

    def _root(self, path: Path) -> _Root:
        resolved = path.resolve()
        workspace = self._workspace.resolve()
        if resolved.is_relative_to(workspace):
            key = resolved.relative_to(workspace)
        else:
            key = Path(OUTSIDE_WORKSPACE, *resolved.parts[1:])
        return _Root(resolved, self._build_directory / PROJECT_BUILDS / key)

    def _module(self, root: _Root) -> GoModuleFile:
        module_file = root.path / MODULE_FILE
        try:
            return go_module_file(module_file.read_text(encoding="utf-8"))
        except OSError:
            shown = self._shown(module_file)
            raise RunnerStartError(
                f"{shown} is missing; restore it with cstudy start <slug> --restore {MODULE_FILE}"
            ) from None

    def _go_line(self, root: _Root) -> str | None:
        try:
            return go_module_file((root.path / MODULE_FILE).read_text(encoding="utf-8")).go
        except OSError:
            return None

    def _first_build(self, marker: str, notify: ProgressNotice) -> bool:
        """Whether no build of this kind left `marker` yet; before the first build of all, says
        that it compiles the runner and the standard library."""
        cold = not (self._build_directory / WARM_MARKER).is_file()
        if cold:
            notify(COLD_NOTICE)
        return cold or not (self._build_directory / marker).is_file()

    def _write_work_file(self, root: _Root, go: str | None) -> None:
        write_if_changed(self._build_directory / MODULE_FILE, build_module_source())
        start = root.directory
        runners = relative(self._runners, start)
        replaces = "".join(
            f"replace {module} => {runners}/{vendored_path(module)}\n"
            for module in VENDORED_MODULES
        )
        uses = "".join(
            f"\t{relative(directory, start)}\n" for directory in (self._build_directory, root.path)
        )
        write_if_changed(
            root.work_file,
            f"go {_newer(go, GO_VERSION)}\n\nuse (\n{uses})\n\n"
            f"replace {RUNNER_MODULE} => {runners}\n{replaces}",
        )

    def _build_suite(self, root: _Root, cold: bool) -> Path:
        main = self._build_directory / "cmd" / SUITE_SCOPE / "main.go"
        write_if_changed(main, _suite_main())
        binary = self._build_directory / "bin" / SUITE_SCOPE / SUITE_BINARY
        outcome = self.build(["-json", "-o", str(binary), f"./cmd/{SUITE_SCOPE}"], root)
        if outcome.exit_code != 0:
            tail = output_text(outcome.stdout, outcome.stderr)[-OUTPUT_TAIL_LINES:]
            raise RunnerStartError("the Go suite runner does not build", tail)
        if cold:
            self.build(list(TEST_FRAMEWORK_PACKAGES), root)
        (self._build_directory / WARM_MARKER).touch()
        (self._build_directory / SUITE_WARM_MARKER).touch()
        return binary

    def _shown(self, path: Path) -> str:
        workspace = self._workspace.resolve()
        return (
            path.relative_to(workspace).as_posix() if path.is_relative_to(workspace) else str(path)
        )


class _GradingBuild:
    """The grading binary of one root: two passes, as for practice files, then a runner that
    reports the project's compile errors when it has some."""

    def __init__(
        self, builds: GoProjectBuilds, root: _Root, meta: ProblemMeta, level: int, module: str
    ) -> None:
        assert meta.project is not None
        self._builds = builds
        self._root = root
        self._meta = meta
        entry_directory = posixpath.dirname(meta.project.entry)
        self._package_directory = root.path / entry_directory if entry_directory else root.path
        import_path = f"{module}/{entry_directory}" if entry_directory else module
        signature = graded_signature(meta.signature, level)
        constructor = constructor_name(signature.name, Language.GO) or f"New{signature.name}"
        self._package = GoPackage(
            COMPILED_USER_TARGET,
            import_path,
            package_clause(_read(root.path / meta.project.entry), entry_directory or "main"),
            constructor,
            root.directory / REGISTRATION_FILE,
            ThunkFile(root.directory / THUNK_FILE, signature),
        )
        self._thunk_file = root.directory / THUNK_FILE
        directory = builds.build_directory
        self._main = directory / "cmd" / PROJECT_BINARIES / meta.snake_slug / "main.go"
        self._binary = directory / "bin" / PROJECT_BINARIES / meta.snake_slug

    def build(self) -> Path:
        unavailable: dict[str, str] = {}
        with_thunks = True
        for _ in range(BUILD_PASSES):
            self._generate(unavailable, with_thunks=with_thunks)
            outcome = self._builds.build(self._arguments(overlay=True), self._root)
            if outcome.exit_code == 0:
                return self._binary
            directory = self._builds.build_directory
            diagnostics = build_diagnostics(outcome.stdout, outcome.stderr, directory)
            if not diagnostics:
                tail = output_text(outcome.stdout, outcome.stderr)[-OUTPUT_TAIL_LINES:]
                raise RunnerStartError(f"go build failed with exit code {outcome.exit_code}", tail)
            in_project = [d for d in diagnostics if d.path.is_relative_to(self._root.path)]
            if in_project:
                return self._build_failure(in_project)
            registration, thunks = self._root.directory / REGISTRATION_FILE, self._thunk_file
            for diagnostic in diagnostics:
                if diagnostic.path == registration.resolve():
                    unavailable[COMPILED_USER_TARGET] = diagnostic.message
                elif diagnostic.path == thunks.resolve():
                    with_thunks = False
                else:
                    lines = [line for d in diagnostics for line in d.shown(str(d.path))]
                    raise RunnerStartError("go build failed", lines[:OUTPUT_TAIL_LINES])
        raise RunnerStartError("the generated Go registration and thunk files do not compile")

    def _generate(self, unavailable: dict[str, str], *, with_thunks: bool) -> None:
        package = self._package
        available = COMPILED_USER_TARGET not in unavailable
        write_if_changed(package.registration, registration_source(package, available))
        thunks = package.thunks
        assert thunks is not None
        write_if_changed(thunks.path, thunk_source(thunks, package.package, with_thunks))
        overlay = {
            self._package_directory / REGISTRATION_FILE: package.registration,
            self._package_directory / THUNK_FILE: thunks.path,
        }
        write_if_changed(self._root.directory / OVERLAY_FILE, overlay_document(overlay))
        write_if_changed(self._main, main_source([package], unavailable))

    def _arguments(self, *, overlay: bool) -> list[str]:
        overlay_flag = [f"-overlay={self._root.directory / OVERLAY_FILE}"] if overlay else []
        package = f"./{self._main.parent.relative_to(self._builds.build_directory).as_posix()}"
        return ["-json", *overlay_flag, "-o", str(self._binary), package]

    def _build_failure(self, diagnostics: list[Diagnostic]) -> Path:
        """A runner without the project, whose jobs report the compiler's lines."""
        lines = [line for d in diagnostics for line in d.shown(self._shown(d.path))]
        first = diagnostics[0]
        trace = f"{self._shown(first.path)}:{first.position.split(':')[0]}"
        message = "\n".join(lines[:MAX_DIAGNOSTIC_LINES])
        write_if_changed(self._main, _build_failure_main(message, trace))
        outcome = self._builds.build(self._arguments(overlay=False), self._root)
        if outcome.exit_code != 0:
            tail = output_text(outcome.stdout, outcome.stderr)[-OUTPUT_TAIL_LINES:]
            raise RunnerStartError("the Go runner does not build", tail)
        return self._binary

    def _shown(self, path: Path) -> str:
        return path.relative_to(self._root.path).as_posix()


def _suite_main() -> str:
    return (
        f'{GENERATED_HEADER}\n\npackage main\n\nimport "{RUNNER_PACKAGE}"\n\n'
        "func main() {\n\trunner.Main(nil, nil, nil)\n}\n"
    )


def _build_failure_main(message: str, trace: str) -> str:
    arguments = ", ".join(json.dumps(text) for text in (COMPILED_USER_TARGET, message, trace))
    return (
        f'{GENERATED_HEADER}\n\npackage main\n\nimport "{RUNNER_PACKAGE}"\n\n'
        f"func main() {{\n\trunner.MainBuildFailed({arguments})\n}}\n"
    )


def _newer(version: str | None, minimum: str) -> str:
    """The newer of two `go` lines; `minimum` when `version` is missing."""
    if version is None:
        return minimum
    found = [int(part) for part in _GO_VERSION_PARTS.findall(version)]
    least = [int(part) for part in _GO_VERSION_PARTS.findall(minimum)]
    return version if found > least else minimum


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
