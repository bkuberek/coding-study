"""`cstudy doctor`: toolchain, config, content and workspace checks
(docs/specs/cli.md#cstudy-doctor,
docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace).

Statuses: `ok`; `warn` for components that are optional or not set up yet (they do not fail
the report); `fail` for anything that blocks practice. `cstudy doctor --fix` runs each workspace
project's setup command first.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import TypeGuard

from coding_study.application.ports import (
    BuildFailed,
    CommandRunner,
    ConfigSource,
    DebugServer,
    DebugServers,
    FolderCheck,
    JdkSelector,
    LanguageRunner,
    ProbeResult,
    ProgressDatabase,
    ProgressNotice,
    ProgressSchema,
    ProjectFolderChecks,
    ProjectLibraries,
    ProjectLinks,
    RepositoryFiles,
    RunnerProcess,
    ScaffoldOutcome,
    Toolchains,
    ToolProbe,
    UserCode,
    WebServerLibraries,
    WebUiAssets,
    WebUiInstall,
    WorkspaceSetup,
)
from coding_study.domain.debugging import (
    DEBUGPY_INSTALL_COMMAND,
    DELVE_VERSION,
    delve_minimum_go,
)
from coding_study.domain.errors import (
    ConfigError,
    LanguageNotSetUpError,
    RunnerProtocolError,
    RunnerStartError,
    UsageError,
)
from coding_study.domain.guides import TOOLCHAINS_GUIDE
from coding_study.domain.jdk import JDK_FIX, SUPPORTED_JDKS, no_jdk_sentence
from coding_study.domain.layout import (
    GO_PROJECT,
    GO_WORK_FILE,
    JVM_PROJECT,
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
from coding_study.domain.project import PROJECT_LANGUAGES
from coding_study.domain.runs import RunnerInfo, RunRequest
from coding_study.domain.signature import FunctionSignature, Returns
from coding_study.domain.type_dsl import VoidType
from coding_study.domain.workspace_projects import (
    PROJECTS_DIRECTORY,
    PYTEST_REQUIREMENT,
)

PYTHON_VERSION = "3.13"
MINIMUM_NODE_MAJOR = 24
MINIMUM_GO = (1, 24)
MINIMUM_RUSTC = (1, 80)
INSTALL_UV = f"install uv: {TOOLCHAINS_GUIDE}#python-and-uv"
INSTALL_PNPM = f"install pnpm: {TOOLCHAINS_GUIDE}#nodejs-and-pnpm"
INSTALL_GO = f"needed for --lang go, install Go 1.24 or newer: {TOOLCHAINS_GUIDE}#go"
INSTALL_RUST = (
    f"needed for --lang rust, install Rust 1.80 or newer with rustup: {TOOLCHAINS_GUIDE}#rust"
)

_DOTTED_VERSION = re.compile(r"(?P<version>\d+(?:\.\d+)+)")


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
    project_links: ProjectLinks
    progress: ProgressDatabase


@dataclass(frozen=True, slots=True)
class DoctorEnvironment:
    tools: ToolProbe
    jdk: JdkSelector
    """The JDK the shell selects, which the `java` row reports."""
    debug_servers: DebugServers
    config: ConfigSource
    content: ContentLocation | NotFound
    workspace: PracticeWorkspace | NotFound
    version: str
    """The running `cstudy` version."""
    web: WebUiInstall
    """What `cstudy serve` needs, for the `web ui assets` and `web server` rows."""


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
PYTEST_CHECK = "python pytest"
PROJECTS_CHECK = "projects"
PROJECT_LINKS_CHECK = "project links"
PROGRESS_CHECK = "progress database"
UPGRADE_CSTUDY = "upgrade cstudy"
VENV_LOCATION_CHECK = f"{PYTHON_PROJECT}/{PYTHON_VENV} location"
VENV_RECREATE_COMMAND = f"rm -rf {PYTHON_PROJECT}/{PYTHON_VENV} && {FIX_COMMAND}"
WEB_ASSETS_CHECK = "web ui assets"
WEB_SERVER_CHECK = "web server"
REINSTALL_COMMAND = "reinstall cstudy"
BYTES_PER_MB = 1_000_000
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
    unless: tuple[str, ...] | None = None
    """A check that runs first, in the project: when it succeeds the step has nothing to do and
    is not run, nor reported."""
    retry: tuple[str, ...] | None = None
    """What runs when `command` fails; the step's outcome is then the retry's."""
    manual: str | None = None
    """What to do by hand when the step fails."""

    def __str__(self) -> str:
        return f"{' '.join(self.command)} (in {self.project})"


PYTHON_FIX = FixStep("python", ("uv", "sync"))
PYTEST_FIX = FixStep(
    PYTHON_PROJECT,
    ("uv", "add", "--dev", "--offline", PYTEST_REQUIREMENT),
    unless=(PYTHON_INTERPRETER, "-c", "import pytest"),
    retry=("uv", "add", "--dev", PYTEST_REQUIREMENT),
    manual=f'once online, run: uv add --dev "{PYTEST_REQUIREMENT}" --directory {PYTHON_PROJECT}',
)
"""Adds pytest to a workspace created before the template listed it. Offline first, which works
whenever uv's cache holds pytest; online only when it does not."""
TYPESCRIPT_FIX = FixStep("typescript", ("pnpm", "install"))
RUNNER_TYPESCRIPT_FIX = FixStep(RUNNER_TYPESCRIPT, ("pnpm", "install"))
JVM_FIX = FixStep(
    "jvm",
    (
        "./gradlew",
        ":java:csClasspath",
        ":kotlin:csClasspath",
        f"-Pcs.only={HANDSHAKE_META.snake_slug}",
    ),
)
"""Builds the runner and support classes and warms the Gradle daemon. Resolving the runtime
classpath caches the runner's own libraries, without which no JVM problem builds offline; `cs.only`
names no practice package, so a half-written practice file never fails the setup."""
NO_JAVA_REASON = "java is not installed or does not run"
NO_JAVA_FIX = replace(JVM_FIX, manual=JDK_FIX)
"""The warm-up as it is reported when there is no JDK it can build with."""
JAVA_CHECK = "java"
SUPPORTED_RANGE = f"cstudy supports JDK {SUPPORTED_JDKS.minimum} to {SUPPORTED_JDKS.maximum}"
JVM_PROJECT_LANGUAGES = (Language.JAVA, Language.KOTLIN)
PROJECT_WARMUPS = "../.cs/runtime/runners/jvm/project-warmup"
"""From `jvm/`: a project folder per language in the runner runtime, with one test each."""
JVM_PROJECT_WARMUPS = tuple(
    FixStep(
        "jvm",
        (
            "./gradlew",
            "-p",
            f"{PROJECT_WARMUPS}/{language}",
            "-q",
            "--console=plain",
            "csClasspath",
        ),
    )
    for language in JVM_PROJECT_LANGUAGES
)
"""Caches what Java and Kotlin project folders build with offline, JUnit, kotlin-test and their
dependencies, which no single-file problem needs (docs/specs/installation-and-workspaces.md)."""


@dataclass(frozen=True, slots=True)
class FixOutcome:
    step: FixStep
    result: ProbeResult | None
    """None when the command's executable is missing."""
    skipped: str | None = None
    """Why the step did not run at all: it would only have failed."""

    @property
    def succeeded(self) -> bool:
        return self.skipped is None and _succeeded(self.result)

    @property
    def detail(self) -> str:
        if self.skipped is not None:
            return f"skipped: {self.skipped}"
        if self.result is None:
            return f"{self.step.command[0]} not found on PATH"
        return f"exited with {self.result.exit_code}" if self.result.exit_code else ""


def repair_workspace(workspace: PracticeWorkspace, notify: ProgressNotice) -> ScaffoldOutcome:
    """Write the missing template files (never touching existing ones, so practice files are
    safe), link the Python project folders to the venv again, and bring the runner runtime in
    step with the content."""
    root = workspace.files.root
    restored = workspace.setup.write_missing(root)
    for relative in restored.written:
        notify(f"restored {relative}")
    for folder in workspace.project_links.relink(root):
        notify(f"relinked {folder}/{PYTHON_VENV}")
    for runner in _folder_checking_runners(workspace):
        for path in runner.repair_folders():
            notify(f"wrote {path}")
    workspace.setup.refresh_runtime(root)
    _migrate_progress(workspace.progress, notify)
    return restored


def _migrate_progress(progress: ProgressDatabase, notify: ProgressNotice) -> None:
    """Migrate an older progress.db now rather than on the next command that opens it; a newer
    or unreadable one stays as it is, for the check to report."""
    try:
        schema = progress.schema()
        if schema.found is None or schema.found >= schema.latest:
            return
        progress.migrate()
    except UsageError as error:
        notify(f"progress.db stays as it is: {error}")
        return
    notify(f"migrated progress.db from schema {schema.found} to {schema.latest}")


def fix_workspace(
    workspace: PracticeWorkspace,
    content: ContentLocation | NotFound,
    jdk: JdkSelector,
    notify: ProgressNotice,
) -> tuple[FixOutcome, ...]:
    """Run the setup command of every workspace project that exists, and in a content checkout
    the TypeScript runner's install, before the JVM warm-up. The Python project then gets
    pytest when its venv lacks it."""
    outcomes: list[FixOutcome] = []
    jvm_blocker = _jvm_warm_up_blocker(workspace, jdk)
    for step, directory in _fix_plan(workspace, content, jvm_blocker is None):
        outcome = _run_step(workspace.commands, step, directory, notify)
        if outcome is not None:
            outcomes.append(outcome)
    if jvm_blocker is not None:
        outcomes.append(FixOutcome(NO_JAVA_FIX, None, skipped=jvm_blocker))
    return tuple(outcomes)


def _jvm_warm_up_blocker(workspace: PracticeWorkspace, jdk: JdkSelector) -> str | None:
    """Why a workspace with a JVM project cannot warm Gradle up: no JDK, or one older than the
    supported minimum, on which Gradle would only fail. A JDK above the range warms up, so the
    problems that opt in to it build offline too."""
    if not workspace.files.exists(JVM_FIX.project):
        return None
    selected = jdk.selected()
    if selected is None:
        return NO_JAVA_REASON
    if selected.feature < SUPPORTED_JDKS.minimum:
        return f"JDK {selected.feature} is older than {SUPPORTED_JDKS.minimum}"
    return None


def _run_step(
    commands: CommandRunner, step: FixStep, directory: Path, notify: ProgressNotice
) -> FixOutcome | None:
    """None when the step's `unless` check succeeds."""
    if step.unless is not None and _succeeded(commands.run(step.unless, directory)):
        return None
    notify(f"running {step}")
    outcome = FixOutcome(step, commands.run(step.command, directory))
    if outcome.succeeded or step.retry is None:
        return outcome
    retried = replace(step, command=step.retry, retry=None)
    notify(f"running {retried}")
    return FixOutcome(retried, commands.run(retried.command, directory))


def _succeeded(result: ProbeResult | None) -> bool:
    return result is not None and result.exit_code == 0


def _fix_plan(
    workspace: PracticeWorkspace, content: ContentLocation | NotFound, jvm: bool
) -> list[tuple[FixStep, Path]]:
    files = workspace.files
    plan = [
        (step, files.root / step.project)
        for step in (PYTHON_FIX, PYTEST_FIX, TYPESCRIPT_FIX)
        if files.exists(step.project)
    ]
    if _is_checkout(content) and content.files.exists(RUNNER_TYPESCRIPT):
        plan.append((RUNNER_TYPESCRIPT_FIX, content.files.root / RUNNER_TYPESCRIPT))
    if jvm and files.exists(JVM_FIX.project):
        plan += [(step, files.root / step.project) for step in (JVM_FIX, *JVM_PROJECT_WARMUPS)]
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
        _java(environment.jdk),
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


def _java(jdk: JdkSelector) -> CheckResult:
    """The selected JDK against the supported range (docs/specs/cli.md#cstudy-doctor). A
    problem's own range is compared where the problem runs, not here."""
    selected = jdk.selected()
    if selected is None:
        java_home = jdk.unusable_java_home()
        return _java_failure(NOT_FOUND if java_home is None else no_jdk_sentence(java_home))
    if selected.feature > SUPPORTED_JDKS.maximum:
        return _java_failure(f"{selected.version} (not supported yet: {SUPPORTED_RANGE})")
    if selected.feature < SUPPORTED_JDKS.minimum:
        return _java_failure(f"{selected.version} (too old: {SUPPORTED_RANGE})")
    return CheckResult(JAVA_CHECK, CheckStatus.OK, f"{selected.version} ({selected.source})")


def _java_failure(detail: str) -> CheckResult:
    return CheckResult(JAVA_CHECK, CheckStatus.FAIL, detail, fix=JDK_FIX)


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
    minimum = delve_minimum_go(version)
    go = _version_of(tools, ("go", "version"))
    if minimum is not None and not isinstance(go, _Unavailable) and not _at_least(go, minimum):
        return _delve_refusing_go(server, version, minimum, go)
    if version != DELVE_VERSION:
        detail = f"{version} (cstudy is tested with {DELVE_VERSION})"
        return CheckResult(server.name, CheckStatus.OK, detail)
    return CheckResult(server.name, CheckStatus.OK, version)


def _delve_refusing_go(
    server: DebugServer, version: str, minimum: tuple[int, int], go: str
) -> CheckResult:
    """Delve refuses a program built with an older Go, though building with it works, so the Go
    row stays as it is and only `--debug` is affected."""
    wanted = _minimum_text(minimum)
    detail = f"{version} (debugs only Go {wanted} or newer; found Go {go})"
    fix = _debugger_fix(server, Language.GO, f"install Go {wanted} or newer")
    return CheckResult(server.name, CheckStatus.WARN, detail, fix=fix)


def _lldb_server(server: DebugServer) -> CheckResult:
    """Only `cstudy test --debug` with Rust needs it, so a missing one warns."""
    if server.path is None:
        fix = _debugger_fix(server, Language.RUST)
        return CheckResult(server.name, CheckStatus.WARN, NOT_FOUND, fix=fix)
    return CheckResult(server.name, CheckStatus.OK, str(server.path))


def _debugger_fix(server: DebugServer, language: Language, step: str | None = None) -> str:
    return (
        f"needed for --debug with --lang {language}, {step or server.install}: "
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
        _projects(files),
        _runtime(workspace),
        _progress_database(workspace.progress),
        *(_workspace_artifact(files, artifact) for artifact in WORKSPACE_ARTIFACTS),
        *_debugpy(environment.tools, files),
        *_pytest(environment.tools, files),
        _project_links(workspace),
        *_folder_checks(workspace),
        *_venv_location(workspace),
        *(_runner(workspace, language, notify) for language in CORE_LANGUAGES),
        *_project_libraries(workspace),
        *_web_ui(environment.web),
    ]


def _workspace_files(workspace: PracticeWorkspace) -> list[CheckResult]:
    """Workspaces from before Go and Rust lack their files, which `--fix` writes, so those only
    warn, and the `projects` check covers the project folders; any other missing file blocks
    practice."""
    missing = workspace.setup.missing_files(workspace.files.root)
    optional = tuple(path for path in missing if _is_optional_language_file(path))
    core = tuple(
        path for path in missing if path not in optional and not _is_in_projects_folder(path)
    )
    return [
        _missing_files("workspace files", core, CheckStatus.FAIL),
        _missing_files(OPTIONAL_LANGUAGE_FILES, optional, CheckStatus.WARN),
    ]


def _is_optional_language_file(path: str) -> bool:
    return path == GO_WORK_FILE or path.split("/")[0] in OPTIONAL_PROJECTS


def _is_in_projects_folder(path: str) -> bool:
    return path.split("/")[0] == PROJECTS_DIRECTORY


def _missing_files(name: str, missing: tuple[str, ...], status: CheckStatus) -> CheckResult:
    return _listed(name, missing, status, "missing")


def _listed(name: str, paths: tuple[str, ...], status: CheckStatus, what: str) -> CheckResult:
    """OK without `paths`; else `status` naming the first few, with the `--fix` command."""
    if not paths:
        return CheckResult(name, CheckStatus.OK)
    detail = f"{len(paths)} {what}: {_first_few(paths, ', ')}"
    return CheckResult(name, status, detail, fix=FIX_COMMAND)


def _first_few(items: tuple[str, ...], separator: str) -> str:
    """The first items, then how many more there are."""
    shown = separator.join(items[:MISSING_FILES_SHOWN])
    more = len(items) - MISSING_FILES_SHOWN
    return shown + (f" and {more} more" if more > 0 else "")


def _projects(files: RepositoryFiles) -> CheckResult:
    """A workspace from before project problems has no `projects/`, which `--fix` writes; only
    project problems use it, so its absence warns."""
    if files.exists(PROJECTS_DIRECTORY):
        return CheckResult(PROJECTS_CHECK, CheckStatus.OK)
    detail = "missing (a workspace from before project problems)"
    return CheckResult(PROJECTS_CHECK, CheckStatus.WARN, detail, fix=FIX_COMMAND)


def _project_links(workspace: PracticeWorkspace) -> CheckResult:
    """A Python project folder reaches the venv through its `.venv` link; without it editors
    and the native `pytest` lose the venv, though `cstudy` still runs, so a broken one warns."""
    unlinked = workspace.project_links.unlinked(workspace.files.root)
    what = f"missing or dangling {PYTHON_VENV} links"
    return _listed(PROJECT_LINKS_CHECK, unlinked, CheckStatus.WARN, what)


def _folder_checks(workspace: PracticeWorkspace) -> list[CheckResult]:
    """What a language checks in its project folders (Go: their `go.work`, vendored `replace`
    and own module path; Rust: their `.cargo/config.toml` and rust-analyzer's link to them);
    editors and native tools need it, `cstudy` does not, so a failure warns."""
    return [
        _folder_row(check)
        for runner in _folder_checking_runners(workspace)
        for check in runner.folder_checks()
    ]


def _folder_row(check: FolderCheck) -> CheckResult:
    """OK without failures; else a warning counting them, naming the first few, with the check's
    own fix or `cstudy doctor --fix`."""
    if not check.failing:
        return CheckResult(check.name, CheckStatus.OK)
    detail = f"{len(check.failing)} {check.problem}: {_first_few(check.failing, check.separator)}"
    return CheckResult(check.name, CheckStatus.WARN, detail, fix=check.fix or FIX_COMMAND)


def _folder_checking_runners(workspace: PracticeWorkspace) -> list[ProjectFolderChecks]:
    runners = (_runner_of(workspace, language) for language in PROJECT_LANGUAGES)
    return [runner for runner in runners if isinstance(runner, ProjectFolderChecks)]


def _runner_of(workspace: PracticeWorkspace, language: Language) -> LanguageRunner | None:
    try:
        return workspace.toolchains.runner(language)
    except LanguageNotSetUpError:
        return None


def _venv_location(workspace: PracticeWorkspace) -> list[CheckResult]:
    """The venv's console scripts keep its absolute path in their shebangs, so after the
    workspace moves they no longer run; `cstudy` runs the interpreter by path and still works.
    Nothing to check before the venv exists."""
    files = workspace.files
    if not files.exists(PYTHON_VENV_ARTIFACT.path):
        return []
    moved = workspace.project_links.moved_venv(files.root)
    if moved is None:
        return [CheckResult(VENV_LOCATION_CHECK, CheckStatus.OK)]
    detail = (
        f"its console scripts name {moved}: the workspace moved, so they no longer run "
        "(cstudy still does)"
    )
    return [CheckResult(VENV_LOCATION_CHECK, CheckStatus.WARN, detail, fix=VENV_RECREATE_COMMAND)]


def _runtime(workspace: PracticeWorkspace) -> CheckResult:
    if workspace.setup.runtime_current(workspace.files.root):
        return CheckResult("runner runtime", CheckStatus.OK, "matches the content")
    detail = "missing or older than the content"
    return CheckResult("runner runtime", CheckStatus.FAIL, detail, fix=FIX_COMMAND)


def _progress_database(progress: ProgressDatabase) -> CheckResult:
    """An older schema migrates on the next command that opens progress.db, so it only warns;
    a newer one was written by a later `cstudy`, which this one cannot read."""
    try:
        schema = progress.schema()
    except UsageError as error:
        return CheckResult(PROGRESS_CHECK, CheckStatus.FAIL, str(error))
    return _progress_schema(schema)


def _progress_schema(schema: ProgressSchema) -> CheckResult:
    if schema.found is None:
        detail = "not created yet (created on first use)"
        return CheckResult(PROGRESS_CHECK, CheckStatus.OK, detail)
    if schema.found > schema.latest:
        detail = f"schema {schema.found} is newer than the {schema.latest} this cstudy reads"
        return CheckResult(PROGRESS_CHECK, CheckStatus.FAIL, detail, fix=UPGRADE_CSTUDY)
    if schema.found < schema.latest:
        detail = (
            f"schema {schema.found}, this cstudy uses {schema.latest}: "
            "migrates on next use; `--fix` migrates now"
        )
        return CheckResult(PROGRESS_CHECK, CheckStatus.WARN, detail, fix=FIX_COMMAND)
    return CheckResult(PROGRESS_CHECK, CheckStatus.OK, f"schema {schema.found}")


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
    if _importable(tools, workspace_files, "debugpy"):
        return [CheckResult(DEBUGPY_CHECK, CheckStatus.OK, "installed (cstudy test --debug)")]
    detail = "not installed (only cstudy test --debug needs it)"
    return [CheckResult(DEBUGPY_CHECK, CheckStatus.WARN, detail, fix=DEBUGPY_INSTALL_COMMAND)]


def _pytest(tools: ToolProbe, workspace_files: RepositoryFiles) -> list[CheckResult]:
    """The runner hosts pytest for a Python project's native tests; nothing else needs it, so a
    missing one only warns. Nothing to check before the venv exists."""
    if not workspace_files.exists(PYTHON_VENV_ARTIFACT.path):
        return []
    if _importable(tools, workspace_files, "pytest"):
        return [CheckResult(PYTEST_CHECK, CheckStatus.OK, "installed (Python project problems)")]
    detail = "not installed (only Python project problems need it)"
    return [CheckResult(PYTEST_CHECK, CheckStatus.WARN, detail, fix=FIX_COMMAND)]


def _importable(tools: ToolProbe, workspace_files: RepositoryFiles, module: str) -> bool:
    interpreter = workspace_files.root / PYTHON_PROJECT / PYTHON_INTERPRETER
    found = tools.run((str(interpreter), "-c", f"import {module}"))
    return found is not None and found.exit_code == 0


def _project_libraries(workspace: PracticeWorkspace) -> list[CheckResult]:
    """Java and Kotlin project folders build offline on libraries the warm-up caches; only
    project problems need them, so missing ones warn. Nothing to check before `jvm/` exists."""
    if not workspace.files.exists(JVM_PROJECT):
        return []
    results: list[CheckResult] = []
    for language in JVM_PROJECT_LANGUAGES:
        runner = workspace.toolchains.runner(language)
        if not isinstance(runner, ProjectLibraries):
            continue
        name = f"{language} project libraries"
        missing = runner.uncached_project_libraries()
        if missing is None:
            detail = f"cached ({language.capitalize()} project problems build offline)"
            results.append(CheckResult(name, CheckStatus.OK, detail))
        else:
            results.append(CheckResult(name, CheckStatus.WARN, missing, fix=FIX_COMMAND))
    return results


def _web_ui(web: WebUiInstall) -> list[CheckResult]:
    """Only `cstudy serve` needs these, so a broken install warns: practice in the terminal
    works without them."""
    return [_web_assets(web.assets()), _web_server(web.server_libraries())]


def _web_assets(assets: WebUiAssets) -> CheckResult:
    if assets.problem is not None:
        return CheckResult(WEB_ASSETS_CHECK, CheckStatus.WARN, assets.problem, REINSTALL_COMMAND)
    size = f"{assets.size_bytes / BYTES_PER_MB:.1f} MB"
    return CheckResult(WEB_ASSETS_CHECK, CheckStatus.OK, f"{size}, digest matches")


def _web_server(libraries: WebServerLibraries) -> CheckResult:
    if libraries.problem is not None:
        return CheckResult(WEB_SERVER_CHECK, CheckStatus.WARN, libraries.problem, REINSTALL_COMMAND)
    return CheckResult(WEB_SERVER_CHECK, CheckStatus.OK, ", ".join(libraries.versions))


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
