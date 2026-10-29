"""The Go `LanguageRunner` (docs/specs/runners.md#go-build-details).

`prepare` generates the build in `.cs/build/go` (a module joined to the workspace's `go/` module
and the runner runtime by a `go.work`), compiles one runner binary for the problem with
`go build -json`, and launches a copy of it that belongs to this run.

Compile errors in the user's or a reference file are a build failure (exit 2). Errors only in a
generated registration file mean the package does not define the expected symbol: the build is
repeated without that registration, and the runner reports a `load_error` for the target with the
compiler's message.

Two `cstudy` processes may build the same problem at once (a watcher and a verify), so the
generation and the build hold an exclusive lock, and each run launches its own copy of the binary,
which no other build overwrites and which `RunnerProcess` removes when the run ends.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.languages.compiled_builds import (
    private_copy,
    relative,
    write_if_changed,
)
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.go.build_files import (
    REGISTRATION_FILE,
    Diagnostic,
    GoPackage,
    build_diagnostics,
    main_source,
    output_text,
    overlay_document,
    package_clause,
    registration_source,
)
from coding_study.adapters.languages.go.toolchain import GoToolchain
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    BuildScope,
    Prepared,
    PrepareResult,
    ProgressNotice,
    References,
    ReferenceSource,
    RunnerLaunch,
    UserCode,
)
from coding_study.domain.errors import (
    ContentError,
    ContentIssue,
    LanguageNotSetUpError,
    RunnerStartError,
)
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
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from coding_study.domain.signature import FunctionSignature

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
COLD_NOTICE = "compiling the Go runner and standard library (first run)"
WARM_BUILD_NOTE = "go, warm"
COLD_BUILD_NOTE = "go, cold"
MAX_DIAGNOSTIC_LINES = 40
OUTPUT_TAIL_LINES = 20
BUILD_PASSES = 2
"""The second pass leaves out the registrations that did not compile; each holds one symbol."""
_MODULE_LINE = re.compile(r"^module\s+(\S+)", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class _Build:
    """One runner binary: which packages it links and where its files go."""

    scope: str
    """`test`, `verify` or `bench`: each keeps its own main package and binary."""
    meta: ProblemMeta
    user: bool
    sources: tuple[ReferenceSource, ...]


class GoRunner:
    """`LanguageRunner` for Go."""

    def __init__(self, context: LanguageContext, toolchain: GoToolchain) -> None:
        self._root = context.workspace.resolve()
        self._runners = context.runners.resolve() / RUNNER_DIRECTORY
        self._project = self._root / GO_PROJECT
        self._build_directory = self._root / BUILD_PROJECT
        self._toolchain = toolchain

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        match scope:
            case UserCode():
                if scope.debug is not None:
                    raise LanguageNotSetUpError(Language.GO, "debug mode")
                build = _Build("test", scope.meta, True, ())
            case References():
                build = _Build("verify", scope.meta, False, scope.sources)
            case BenchCode():
                build = _Build("bench", scope.meta, not scope.references_only, scope.sources)
        return self._prepare(build, notify)

    def _prepare(self, build: _Build, notify: ProgressNotice) -> PrepareResult:
        module = self._workspace_module()
        with exclusive_lock(self._build_directory / LOCK_FILE):
            warm = (self._build_directory / WARM_MARKER).is_file()
            if not warm:
                notify(COLD_NOTICE)
            self._write_module_files()
            packages = self._packages(build, module)
            result = self._compile(build, packages)
            if isinstance(result, BuildFailed):
                return result
            (self._build_directory / WARM_MARKER).touch()
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
        project = relative(self._project, self._build_directory)
        runners = relative(self._runners, self._build_directory)
        write_if_changed(
            self._build_directory / MODULE_FILE,
            f"module {BUILD_MODULE}\n\ngo {GO_VERSION}\n\nrequire {RUNNER_MODULE} v0.0.0\n",
        )
        write_if_changed(
            self._build_directory / WORK_FILE,
            f"go {GO_VERSION}\n\nuse (\n\t.\n\t{project}\n)\n\n"
            f"replace {RUNNER_MODULE} => {runners}\n",
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
        )

    def _compile(self, build: _Build, packages: list[GoPackage]) -> "Path | BuildFailed":
        """The built binary, after a second pass without the registrations that did not
        compile; BuildFailed for errors in user code (and reference code, in verify)."""
        unavailable: dict[str, str] = {}
        for _ in range(BUILD_PASSES):
            arguments = self._generate(build, packages, unavailable)
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
            source_errors = [d for d in diagnostics if d.path not in registrations]
            if source_errors:
                return self._build_failure(build, source_errors)
            for diagnostic in diagnostics:
                unavailable.setdefault(registrations[diagnostic.path].target_id, diagnostic.message)
        raise RunnerStartError("the generated Go registration files do not compile")

    def _generate(
        self, build: _Build, packages: list[GoPackage], unavailable: dict[str, str]
    ) -> list[str]:
        """Writes the registrations, the overlay and the main package; returns the build's
        arguments."""
        overlay: dict[Path, Path] = {}
        for package in packages:
            source = registration_source(package, package.target_id not in unavailable)
            write_if_changed(package.registration, source)
            if package.target_id == COMPILED_USER_TARGET:
                virtual = self._root / stub_path(build.meta, Language.GO)
                overlay[virtual.parent / REGISTRATION_FILE] = package.registration
        main = self._build_directory / "cmd" / build.scope / build.meta.snake_slug / "main.go"
        write_if_changed(main, main_source(packages, unavailable))
        arguments = ["-json"]
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
        return self._build_directory / "bin" / build.scope / build.meta.snake_slug


def _registered_symbol(meta: ProblemMeta) -> str:
    """The function, or the constructor of a class kind, that the registration exposes."""
    signature = meta.signature
    if isinstance(signature, FunctionSignature):
        return member_name(signature.name, Language.GO, NameRole.FUNCTION)
    constructor = constructor_name(signature.name, Language.GO)
    assert constructor is not None
    return constructor


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
