"""`cstudy doctor`: toolchain, config, content and workspace checks
(docs/specs/cli.md#cstudy-doctor,
docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace).

Statuses: `ok`; `warn` for components that are optional or not set up yet (they do not fail
the report); `fail` for anything that blocks practice. `cstudy doctor --fix` runs each workspace
project's setup command first.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypeGuard

from coding_study.application.ports import (
    BuildFailed,
    CommandRunner,
    ConfigSource,
    DebugServer,
    DebugServers,
    ProbeResult,
    ProgressNotice,
    RepositoryFiles,
    RunnerProcess,
    ScaffoldOutcome,
    Toolchains,
    ToolProbe,
    UserCode,
    WorkspaceSetup,
)
from coding_study.domain.debugging import DEBUGPY_INSTALL_COMMAND, DELVE_VERSION
from coding_study.domain.errors import (
    ConfigError,
    LanguageNotSetUpError,
    RunnerProtocolError,
    RunnerStartError,
)
from coding_study.domain.guides import TOOLCHAINS_GUIDE
from coding_study.domain.layout import (
    GO_PROJECT,
    GO_WORK_FILE,
    PYTHON_INTERPRETER,
    PYTHON_PROJECT,
    PYTHON_VENV,
    RUST_PROJECT,
)
from coding_study.domain.problem import (
    CORE_LANGUAGES,
    ComparatorSpec,
    ComparatorType,
    ContentStatus,
    Difficulty,
    Language,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.runs import RunnerInfo, RunRequest
from coding_study.domain.signature import FunctionSignature, Returns
from coding_study.domain.type_dsl import VoidType

PYTHON_VERSION = "3.13"
MINIMUM_NODE_MAJOR = 24
JAVA_MAJOR = 21
MINIMUM_GO = (1, 24)
MINIMUM_RUSTC = (1, 80)
INSTALL_UV = f"install uv: {TOOLCHAINS_GUIDE}#python-and-uv"
INSTALL_PNPM = f"install pnpm: {TOOLCHAINS_GUIDE}#nodejs-and-pnpm"
INSTALL_GO = f"needed for --lang go, install Go 1.24 or newer: {TOOLCHAINS_GUIDE}#go"
INSTALL_RUST = (
    f"needed for --lang rust, install Rust 1.80 or newer with rustup: {TOOLCHAINS_GUIDE}#rust"
)

_DOTTED_VERSION = re.compile(r"(?P<version>\d+(?:\.\d+)+)")
_JAVA_VERSION = re.compile(r'version "(?P<version>\d+(?:\.\d+)*)')


class CheckStatus(StrEnum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    status: CheckStatus
    detail: str = ""
    fix: str | None = None


@dataclass(frozen=True, slots=True)
class DoctorReport:
    results: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.status is not CheckStatus.FAIL for result in self.results)


@dataclass(frozen=True, slots=True)
class NotFound:
    reason: str
    unusable: bool = False
    """The marker is there, but unreadable or of a newer schema: a failure, not a warning."""


@dataclass(frozen=True, slots=True)
class ContentLocation:
    files: RepositoryFiles
    editable: bool
    """A checkout (`cstudy new` writes into it); otherwise the copy bundled with `cstudy`."""


@dataclass(frozen=True, slots=True)
class PracticeWorkspace:
    """A workspace root and the adapters its checks and fixes need."""

    files: RepositoryFiles
    created_with: str
    """The `cstudy` version its marker records."""
    setup: WorkspaceSetup
    toolchains: Toolchains
    """Built against the runner runtime as it is: `--fix` refreshes it, the checks do not."""
    runner_process: RunnerProcess
    commands: CommandRunner


@dataclass(frozen=True, slots=True)
class DoctorEnvironment:
    tools: ToolProbe
    debug_servers: DebugServers
    config: ConfigSource
    content: ContentLocation | NotFound
    workspace: PracticeWorkspace | NotFound
    version: str
    """The running `cstudy` version."""


@dataclass(frozen=True, slots=True)
class _WorkspaceArtifact:
    """A file a workspace project needs once that project exists (docs/architecture.md)."""

    project: str
    artifact: str
    fix_command: str

    @property
    def path(self) -> str:
        return f"{self.project}/{self.artifact}"


NOT_FOUND = "not found"
FIX_COMMAND = "cstudy doctor --fix"
INIT_COMMAND = "cstudy init"
MISSING_FILES_SHOWN = 5
OPTIONAL_LANGUAGE_FILES = "go and rust files"
OPTIONAL_PROJECTS = frozenset({GO_PROJECT, RUST_PROJECT})
PYTHON_VENV_ARTIFACT = _WorkspaceArtifact(PYTHON_PROJECT, PYTHON_VENV, FIX_COMMAND)
WORKSPACE_ARTIFACTS = (
    _WorkspaceArtifact("jvm", "gradlew", "gradle wrapper (in jvm)"),
    PYTHON_VENV_ARTIFACT,
    _WorkspaceArtifact("typescript", "node_modules", FIX_COMMAND),
)
DEBUGPY_CHECK = "python debugpy"
RUNNER_TYPESCRIPT = "runners/typescript"
"""In a content checkout, `--fix` also installs the TypeScript runner's own `tsc` and types."""
HANDSHAKE_META = ProblemMeta(
    id="0000",
    slug="cs-doctor-handshake",
    title="cstudy doctor handshake",
    status=ContentStatus.DRAFT,
    difficulty=Difficulty.EASY,
    track=Track.DSA,
    kind=ProblemKind.FUNCTION,
    signature=FunctionSignature("handshake", (), Returns(VoidType())),
    comparator=ComparatorSpec(ComparatorType.EXACT),
    approaches=(),
)
"""A problem with no files anywhere: preparing it builds only the runner itself."""


@dataclass(frozen=True, slots=True)
class FixStep:
    project: str
    """Relative to the workspace, or `runners/typescript` of the content checkout."""
    command: tuple[str, ...]

    def __str__(self) -> str:
        return f"{' '.join(self.command)} (in {self.project})"


PYTHON_FIX = FixStep("python", ("uv", "sync"))
TYPESCRIPT_FIX = FixStep("typescript", ("pnpm", "install"))
RUNNER_TYPESCRIPT_FIX = FixStep(RUNNER_TYPESCRIPT, ("pnpm", "install"))
JVM_FIX = FixStep(
    "jvm",
    ("./gradlew", ":java:classes", ":kotlin:classes", f"-Pcs.only={HANDSHAKE_META.snake_slug}"),
)
"""Builds the runner and support classes and warms the Gradle daemon; `cs.only` names no
practice package, so a half-written practice file never fails the setup."""


@dataclass(frozen=True, slots=True)
class FixOutcome:
    step: FixStep
    result: ProbeResult | None
    """None when the command's executable is missing."""

    @property
    def succeeded(self) -> bool:
        return self.result is not None and self.result.exit_code == 0

    @property
    def detail(self) -> str:
        if self.result is None:
            return f"{self.step.command[0]} not found on PATH"
        return f"exited with {self.result.exit_code}" if self.result.exit_code else ""


def repair_workspace(workspace: PracticeWorkspace, notify: ProgressNotice) -> ScaffoldOutcome:
    """Write the missing template files (never touching existing ones, so practice files are
    safe) and bring the runner runtime in step with the content."""
    root = workspace.files.root
    restored = workspace.setup.write_missing(root)
    for relative in restored.written:
        notify(f"restored {relative}")
    workspace.setup.refresh_runtime(root)
    return restored


def fix_workspace(
    workspace: PracticeWorkspace, content: ContentLocation | NotFound, notify: ProgressNotice
) -> tuple[FixOutcome, ...]:
    """Run the setup command of every workspace project that exists, and in a content checkout
    the TypeScript runner's install, before the JVM warm-up."""
    outcomes: list[FixOutcome] = []
    for step, directory in _fix_plan(workspace, content):
        notify(f"running {step}")
        outcomes.append(FixOutcome(step, workspace.commands.run(step.command, directory)))
    return tuple(outcomes)


def _fix_plan(
    workspace: PracticeWorkspace, content: ContentLocation | NotFound
) -> list[tuple[FixStep, Path]]:
    files = workspace.files
    plan = [
        (step, files.root / step.project)
        for step in (PYTHON_FIX, TYPESCRIPT_FIX)
        if files.exists(step.project)
    ]
    if _is_checkout(content) and content.files.exists(RUNNER_TYPESCRIPT):
        plan.append((RUNNER_TYPESCRIPT_FIX, content.files.root / RUNNER_TYPESCRIPT))
    if files.exists(JVM_FIX.project):
        plan.append((JVM_FIX, files.root / JVM_FIX.project))
    return plan


def _is_checkout(content: ContentLocation | NotFound) -> TypeGuard[ContentLocation]:
    return isinstance(content, ContentLocation) and content.editable


def run_doctor(environment: DoctorEnvironment, notify: ProgressNotice) -> DoctorReport:
    tools = environment.tools
    results = [
        _python(tools),
        _present_tool(tools, "uv", INSTALL_UV),
        _node(tools),
        _present_tool(tools, "pnpm", INSTALL_PNPM),
        _java(tools),
        _gradle(tools),
        _go(tools),
        _rustc(tools),
        _cargo(tools),
        _delve(tools, environment.debug_servers.delve()),
        _lldb_server(environment.debug_servers.lldb_server()),
        _config(environment.config),
        _content(environment.content),
        *_workspace(environment, notify),
    ]
    return DoctorReport(tuple(results))


@dataclass(frozen=True, slots=True)
class _Unavailable:
    reason: str


def _version_of(
    tools: ToolProbe, command: Sequence[str], pattern: re.Pattern[str] = _DOTTED_VERSION
) -> str | _Unavailable:
    result = tools.run(command)
    command_text = " ".join(command)
    if result is None:
        return _Unavailable("not found on PATH")
    if result.exit_code != 0:
        return _Unavailable(f"`{command_text}` exited with {result.exit_code}")
    found = pattern.search(result.output)
    if found is None:
        return _Unavailable(f"`{command_text}` printed no version")
    return found["version"]


def _major(version: str) -> int:
    return int(version.split(".")[0])


def _python(tools: ToolProbe) -> CheckResult:
    found = tools.run(("uv", "python", "find", PYTHON_VERSION))
    if found is None:
        return CheckResult(
            "python",
            CheckStatus.FAIL,
            f"uv not found (uv provides Python {PYTHON_VERSION})",
            fix=INSTALL_UV,
        )
    interpreters = found.output.strip().splitlines()
    if found.exit_code != 0 or not interpreters:
        return CheckResult(
            "python",
            CheckStatus.FAIL,
            f"Python {PYTHON_VERSION} not found",
            fix=f"uv python install {PYTHON_VERSION}",
        )
    return _present_version("python", _version_of(tools, (interpreters[0], "--version")), None)


def _present_tool(tools: ToolProbe, name: str, fix: str) -> CheckResult:
    return _present_version(name, _version_of(tools, (name, "--version")), fix)


def _present_version(name: str, version: str | _Unavailable, fix: str | None) -> CheckResult:
    if isinstance(version, _Unavailable):
        return CheckResult(name, CheckStatus.FAIL, version.reason, fix=fix)
    return CheckResult(name, CheckStatus.OK, version)


def _node(tools: ToolProbe) -> CheckResult:
    version = _version_of(tools, ("node", "--version"))
    fix = f"install Node {MINIMUM_NODE_MAJOR} or newer: {TOOLCHAINS_GUIDE}#nodejs-and-pnpm"
    if isinstance(version, _Unavailable):
        return CheckResult("node", CheckStatus.FAIL, version.reason, fix=fix)
    if _major(version) < MINIMUM_NODE_MAJOR:
        detail = f"v{version} (need {MINIMUM_NODE_MAJOR} or newer for type stripping)"
        return CheckResult("node", CheckStatus.FAIL, detail, fix=fix)
    return CheckResult("node", CheckStatus.OK, f"v{version} (type stripping)")


def _java(tools: ToolProbe) -> CheckResult:
    version = _version_of(tools, ("java", "-version"), _JAVA_VERSION)
    fix = f"install JDK {JAVA_MAJOR}: {TOOLCHAINS_GUIDE}#jdk-{JAVA_MAJOR}"
    if isinstance(version, _Unavailable):
        return CheckResult("java", CheckStatus.FAIL, version.reason, fix=fix)
    if _major(version) != JAVA_MAJOR:
        return CheckResult("java", CheckStatus.FAIL, f"{version} (need JDK {JAVA_MAJOR})", fix=fix)
    return CheckResult("java", CheckStatus.OK, version)


def _gradle(tools: ToolProbe) -> CheckResult:
    """Homebrew Gradle only generates the committed wrapper, so its absence is a warning."""
    version = _version_of(tools, ("gradle", "--version"))
    if isinstance(version, _Unavailable):
        detail = f"{version.reason} (only needed to regenerate the Gradle wrapper)"
        return CheckResult("gradle", CheckStatus.WARN, detail, fix="brew install gradle")
    return CheckResult("gradle", CheckStatus.OK, version)


def _at_least(version: str, minimum: tuple[int, int]) -> bool:
    major, minor, *_ = (int(part) for part in version.split("."))
    return (major, minor) >= minimum


def _minimum_text(minimum: tuple[int, int]) -> str:
    return ".".join(str(part) for part in minimum)


def _go(tools: ToolProbe) -> CheckResult:
    """Only `--lang go` needs Go, so a missing or old one warns."""
    version = _version_of(tools, ("go", "version"))
    if isinstance(version, _Unavailable):
        return CheckResult("go", CheckStatus.WARN, version.reason, fix=INSTALL_GO)
    if not _at_least(version, MINIMUM_GO):
        detail = (
            f"{version} (need {_minimum_text(MINIMUM_GO)} or newer; "
            "cstudy builds with GOTOOLCHAIN=local and never downloads one)"
        )
        return CheckResult("go", CheckStatus.WARN, detail, fix=INSTALL_GO)
    return CheckResult("go", CheckStatus.OK, version)


def _rustc(tools: ToolProbe) -> CheckResult:
    """Only `--lang rust` needs Rust, so a missing or old one warns."""
    version = _version_of(tools, ("rustc", "--version"))
    if isinstance(version, _Unavailable):
        return CheckResult("rustc", CheckStatus.WARN, version.reason, fix=INSTALL_RUST)
    if not _at_least(version, MINIMUM_RUSTC):
        detail = f"{version} (need {_minimum_text(MINIMUM_RUSTC)} or newer)"
        return CheckResult("rustc", CheckStatus.WARN, detail, fix=INSTALL_RUST)
    return CheckResult("rustc", CheckStatus.OK, version)


def _cargo(tools: ToolProbe) -> CheckResult:
    version = _version_of(tools, ("cargo", "--version"))
    if isinstance(version, _Unavailable):
        return CheckResult("cargo", CheckStatus.WARN, version.reason, fix=INSTALL_RUST)
    return CheckResult("cargo", CheckStatus.OK, version)


def _delve(tools: ToolProbe, server: DebugServer) -> CheckResult:
    """Only `cstudy test --debug` with Go needs Delve, so a missing one warns; another release
    than the tested one may work, so it passes."""
    fix = _debugger_fix(server, Language.GO)
    if server.path is None:
        return CheckResult(server.name, CheckStatus.WARN, NOT_FOUND, fix=fix)
    version = _version_of(tools, (str(server.path), "version"))
    if isinstance(version, _Unavailable):
        return CheckResult(server.name, CheckStatus.WARN, version.reason, fix=fix)
    if version != DELVE_VERSION:
        detail = f"{version} (cstudy is tested with {DELVE_VERSION})"
        return CheckResult(server.name, CheckStatus.OK, detail)
    return CheckResult(server.name, CheckStatus.OK, version)


def _lldb_server(server: DebugServer) -> CheckResult:
    """Only `cstudy test --debug` with Rust needs it, so a missing one warns."""
    if server.path is None:
        fix = _debugger_fix(server, Language.RUST)
        return CheckResult(server.name, CheckStatus.WARN, NOT_FOUND, fix=fix)
    return CheckResult(server.name, CheckStatus.OK, str(server.path))


def _debugger_fix(server: DebugServer, language: Language) -> str:
    return (
        f"needed for --debug with --lang {language}, {server.install}: "
        f"{TOOLCHAINS_GUIDE}#{language}"
    )


def _config(source: ConfigSource) -> CheckResult:
    if not source.exists():
        return CheckResult(
            "config", CheckStatus.OK, f"{source.location} (not found, using defaults)"
        )
    try:
        source.load()
    except ConfigError as error:
        return CheckResult(
            "config", CheckStatus.FAIL, f"{source.location}: {'; '.join(error.issues)}"
        )
    return CheckResult("config", CheckStatus.OK, source.location)


def _content(content: ContentLocation | NotFound) -> CheckResult:
    if isinstance(content, NotFound):
        return CheckResult("content", CheckStatus.FAIL, content.reason)
    kind = "checkout" if content.editable else "bundled"
    return CheckResult("content", CheckStatus.OK, f"{content.files.root} ({kind})")


def _workspace(environment: DoctorEnvironment, notify: ProgressNotice) -> list[CheckResult]:
    workspace = environment.workspace
    if isinstance(workspace, NotFound):
        if workspace.unusable:
            return [CheckResult("workspace", CheckStatus.FAIL, workspace.reason)]
        return [CheckResult("workspace", CheckStatus.WARN, workspace.reason, fix=INIT_COMMAND)]
    files = workspace.files
    created = f"created with cstudy {workspace.created_with}"
    if workspace.created_with != environment.version:
        created += f", running {environment.version}"
    return [
        CheckResult("workspace", CheckStatus.OK, f"{files.root} ({created})"),
        *_workspace_files(workspace),
        _runtime(workspace),
        *(_workspace_artifact(files, artifact) for artifact in WORKSPACE_ARTIFACTS),
        *_debugpy(environment.tools, files),
        *(_runner(workspace, language, notify) for language in CORE_LANGUAGES),
    ]


def _workspace_files(workspace: PracticeWorkspace) -> list[CheckResult]:
    """Workspaces from before Go and Rust lack their files, which `--fix` writes, so those only
    warn; any other missing file blocks practice."""
    missing = workspace.setup.missing_files(workspace.files.root)
    optional = tuple(path for path in missing if _is_optional_language_file(path))
    core = tuple(path for path in missing if path not in optional)
    return [
        _missing_files("workspace files", core, CheckStatus.FAIL),
        _missing_files(OPTIONAL_LANGUAGE_FILES, optional, CheckStatus.WARN),
    ]


def _is_optional_language_file(path: str) -> bool:
    return path == GO_WORK_FILE or path.split("/")[0] in OPTIONAL_PROJECTS


def _missing_files(name: str, missing: tuple[str, ...], status: CheckStatus) -> CheckResult:
    if not missing:
        return CheckResult(name, CheckStatus.OK)
    shown = ", ".join(missing[:MISSING_FILES_SHOWN])
    more = len(missing) - MISSING_FILES_SHOWN
    detail = f"{len(missing)} missing: {shown}" + (f" and {more} more" if more > 0 else "")
    return CheckResult(name, status, detail, fix=FIX_COMMAND)


def _runtime(workspace: PracticeWorkspace) -> CheckResult:
    if workspace.setup.runtime_current(workspace.files.root):
        return CheckResult("runner runtime", CheckStatus.OK, "matches the content")
    detail = "missing or older than the content"
    return CheckResult("runner runtime", CheckStatus.FAIL, detail, fix=FIX_COMMAND)


def _workspace_artifact(repository: RepositoryFiles, artifact: _WorkspaceArtifact) -> CheckResult:
    if not repository.exists(artifact.project):
        return CheckResult(
            artifact.path, CheckStatus.WARN, f"not set up yet (no {artifact.project})"
        )
    if repository.exists(artifact.path):
        return CheckResult(artifact.path, CheckStatus.OK)
    return CheckResult(artifact.path, CheckStatus.FAIL, "missing", fix=artifact.fix_command)


def _debugpy(tools: ToolProbe, workspace_files: RepositoryFiles) -> list[CheckResult]:
    """`cstudy test --debug` attaches through debugpy; practice without debugging never needs it,
    so a missing one only warns. Nothing to check before the venv exists."""
    if not workspace_files.exists(PYTHON_VENV_ARTIFACT.path):
        return []
    interpreter = workspace_files.root / PYTHON_PROJECT / PYTHON_INTERPRETER
    found = tools.run((str(interpreter), "-c", "import debugpy"))
    if found is not None and found.exit_code == 0:
        return [CheckResult(DEBUGPY_CHECK, CheckStatus.OK, "installed (cstudy test --debug)")]
    detail = "not installed (only cstudy test --debug needs it)"
    return [CheckResult(DEBUGPY_CHECK, CheckStatus.WARN, detail, fix=DEBUGPY_INSTALL_COMMAND)]


def _runner(
    workspace: PracticeWorkspace, language: Language, notify: ProgressNotice
) -> CheckResult:
    """Only the core languages answer a handshake; Go and Rust are covered by their toolchain
    rows, so a machine without them passes."""
    name = f"runner {language}"
    hello = _hello(workspace, language, notify)
    if isinstance(hello, RunnerInfo):
        detail = f"answers hello: {hello.runner} {hello.runtime}, protocol {hello.protocol}"
        features = "".join(f", {feature}" for feature in hello.features)
        return CheckResult(name, CheckStatus.OK, detail + features)
    return CheckResult(name, CheckStatus.FAIL, hello.reason, fix=FIX_COMMAND)


def _hello(
    workspace: PracticeWorkspace, language: Language, notify: ProgressNotice
) -> RunnerInfo | _Unavailable:
    """Prepare the runner for a problem with no code and start it with no jobs."""
    try:
        prepared = workspace.toolchains.runner(language).prepare(UserCode(HANDSHAKE_META), notify)
        if isinstance(prepared, BuildFailed):
            return _Unavailable(f"does not build: {' | '.join(prepared.diagnostics)}")
        return workspace.runner_process.run(prepared.launch, RunRequest(())).runner
    except (RunnerStartError, RunnerProtocolError, LanguageNotSetUpError) as error:
        return _Unavailable(str(error).splitlines()[0])
