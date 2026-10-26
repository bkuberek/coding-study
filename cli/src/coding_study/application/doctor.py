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
from coding_study.domain.errors import (
    ConfigError,
    LanguageNotSetUpError,
    RunnerProtocolError,
    RunnerStartError,
)
from coding_study.domain.problem import (
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


FIX_COMMAND = "cstudy doctor --fix"
INIT_COMMAND = "cstudy init"
MISSING_FILES_SHOWN = 5
WORKSPACE_ARTIFACTS = (
    _WorkspaceArtifact("jvm", "gradlew", "gradle wrapper (in jvm)"),
    _WorkspaceArtifact("python", ".venv", FIX_COMMAND),
    _WorkspaceArtifact("typescript", "node_modules", FIX_COMMAND),
)
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
        _present_tool(tools, "uv", "install uv: https://docs.astral.sh/uv/"),
        _node(tools),
        _present_tool(tools, "pnpm", "install pnpm"),
        _java(tools),
        _gradle(tools),
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
            "python", CheckStatus.FAIL, f"uv not found (uv provides Python {PYTHON_VERSION})"
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
    fix = f"install Node {MINIMUM_NODE_MAJOR} or newer"
    if isinstance(version, _Unavailable):
        return CheckResult("node", CheckStatus.FAIL, version.reason, fix=fix)
    if _major(version) < MINIMUM_NODE_MAJOR:
        detail = f"v{version} (need {MINIMUM_NODE_MAJOR} or newer for type stripping)"
        return CheckResult("node", CheckStatus.FAIL, detail, fix=fix)
    return CheckResult("node", CheckStatus.OK, f"v{version} (type stripping)")


def _java(tools: ToolProbe) -> CheckResult:
    version = _version_of(tools, ("java", "-version"), _JAVA_VERSION)
    fix = f"install JDK {JAVA_MAJOR}"
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
        _workspace_files(workspace),
        _runtime(workspace),
        *(_workspace_artifact(files, artifact) for artifact in WORKSPACE_ARTIFACTS),
        *(_runner(workspace, language, notify) for language in Language),
    ]


def _workspace_files(workspace: PracticeWorkspace) -> CheckResult:
    missing = workspace.setup.missing_files(workspace.files.root)
    if not missing:
        return CheckResult("workspace files", CheckStatus.OK)
    shown = ", ".join(missing[:MISSING_FILES_SHOWN])
    more = len(missing) - MISSING_FILES_SHOWN
    detail = f"{len(missing)} missing: {shown}" + (f" and {more} more" if more > 0 else "")
    return CheckResult("workspace files", CheckStatus.FAIL, detail, fix=FIX_COMMAND)


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


def _runner(
    workspace: PracticeWorkspace, language: Language, notify: ProgressNotice
) -> CheckResult:
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
