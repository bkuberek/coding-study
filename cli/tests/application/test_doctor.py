from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.application.doctor import (
    HANDSHAKE_META,
    JVM_FIX,
    JVM_PROJECT_WARMUPS,
    CheckResult,
    CheckStatus,
    ContentLocation,
    DoctorEnvironment,
    DoctorReport,
    FixStep,
    NotFound,
    PracticeWorkspace,
    fix_sandbox,
    fix_workspace,
    repair_workspace,
    run_doctor,
)
from coding_study.application.installs import Install, InstallKind, InstallScan
from coding_study.application.ports import (
    BuildFailed,
    BuildScope,
    CaseListener,
    DebugServer,
    FolderCheck,
    LanguageRunner,
    Prepared,
    PrepareResult,
    ProbeResult,
    ProgressNotice,
    ProgressSchema,
    RunnerLaunch,
    ScaffoldOutcome,
    SuiteListener,
    UserCode,
    WebServerLibraries,
    WebUiAssets,
    WebUiInstall,
)
from coding_study.domain.bench_runs import BenchReport, BenchRequest
from coding_study.domain.config import Config
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.errors import (
    ConfigError,
    RunnerProtocolError,
    RunnerStartError,
    UsageError,
)
from coding_study.domain.jdk import JDK_FIX, JdkSource, SelectedJdk
from coding_study.domain.problem import Language
from coding_study.domain.runs import RunnerInfo, RunReport, RunRequest
from coding_study.domain.sandbox import SandboxInventory, StackContainer, StackResource
from coding_study.domain.suite_runs import SuiteJob, SuiteReport
from coding_study.domain.workspace_projects import PYTEST_REQUIREMENT
from tests.fakes import (
    DEBUGSERVER,
    DELVE,
    FakeDebugServers,
    FakeLanguageRunner,
    FakeLanguageServers,
    FakeToolchains,
    MemoryPreferences,
)
from tests.sandbox_fakes import FakeSandbox

OK, WARN, FAIL = CheckStatus.OK, CheckStatus.WARN, CheckStatus.FAIL
PYTHON_PATH = "/py/bin/python3.13"
WORKSPACE_PYTHON = "/ws/python/.venv/bin/python"
IMPORT_DEBUGPY = (WORKSPACE_PYTHON, "-c", "import debugpy")
IMPORT_PYTEST = (WORKSPACE_PYTHON, "-c", "import pytest")
DELVE_VERSION = ("/go/bin/dlv", "version")
HEALTHY_TOOLS: dict[tuple[str, ...], ProbeResult] = {
    ("uv", "python", "find", "3.13"): ProbeResult(0, f"{PYTHON_PATH}\n"),
    (PYTHON_PATH, "--version"): ProbeResult(0, "Python 3.13.2\n"),
    ("uv", "--version"): ProbeResult(0, "uv 0.10.11 (006b56b12 2026-03-16)\n"),
    ("node", "--version"): ProbeResult(0, "v24.18.0\n"),
    ("pnpm", "--version"): ProbeResult(0, "9.15.9\n"),
    ("gradle", "--version"): ProbeResult(0, "\n------\nGradle 9.8.2\n------\n"),
    ("go", "version"): ProbeResult(0, "go version go1.25.0 darwin/arm64\n"),
    ("rustc", "--version"): ProbeResult(0, "rustc 1.80.0 (051478957 2024-07-21)\n"),
    ("cargo", "--version"): ProbeResult(0, "cargo 1.80.0 (376290515 2024-07-16)\n"),
    DELVE_VERSION: ProbeResult(0, "Delve Debugger\nVersion: 1.27.2\nBuild: $Id: 360e7b2 $\n"),
    IMPORT_DEBUGPY: ProbeResult(0, ""),
    IMPORT_PYTEST: ProbeResult(0, ""),
}
COMPLETE_WORKSPACE = {
    "jvm",
    "jvm/gradlew",
    "projects",
    "python",
    "python/.venv",
    "typescript",
    "typescript/node_modules",
}
RUNNING_VERSION = "0.1.0"
IMPORT_PYTEST_IN_PYTHON = ((".venv/bin/python", "-c", "import pytest"), Path("/ws/python"))
ADD_PYTEST_OFFLINE = ("uv", "add", "--dev", "--offline", PYTEST_REQUIREMENT)
ADD_PYTEST = ("uv", "add", "--dev", PYTEST_REQUIREMENT)
TOOLCHAINS_GUIDE = "https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md"
SELECT_A_JDK = f"select a JDK 21 to 26 with JAVA_HOME, or install JDK 25: {TOOLCHAINS_GUIDE}#jdk"
"""The fix of docs/specs/cli.md#cstudy-doctor, for any JDK that cannot run Java and Kotlin."""
JDK_25 = SelectedJdk("25.0.5", 25, JdkSource.JAVA_HOME)
JDK_HOME = Path("/opt/jdks/25")


@dataclass
class FakeJdk:
    """The JDK the shell selects, or why there is none."""

    jdk: SelectedJdk | None = JDK_25
    java_home_without_jdk: str | None = None
    asked: int = 0
    home: Path = JDK_HOME

    def selected(self) -> SelectedJdk | None:
        self.asked += 1
        return self.jdk

    def unusable_java_home(self) -> str | None:
        return self.java_home_without_jdk

    def selected_home(self) -> Path | None:
        return None if self.jdk is None else self.home


@dataclass
class FakeTools:
    outputs: dict[tuple[str, ...], ProbeResult | None] = field(
        default_factory=lambda: dict(HEALTHY_TOOLS)
    )

    def run(self, command: Sequence[str]) -> ProbeResult | None:
        return self.outputs.get(tuple(command))


@dataclass
class FakeConfigSource:
    present: bool = False
    issues: tuple[str, ...] = ()
    location: str = "/home/user/.config/coding-study/config.toml"

    def exists(self) -> bool:
        return self.present

    def load(self) -> Config:
        if self.issues:
            raise ConfigError(self.location, self.issues)
        return Config()


@dataclass
class FakeFiles:
    paths: set[str] = field(default_factory=set)
    root: Path = Path("/ws")

    def exists(self, relative_path: str) -> bool:
        return relative_path in self.paths


BUNDLED = ContentLocation(FakeFiles({"runners/typescript"}, Path("/tool/content")), False)
CHECKOUT = ContentLocation(FakeFiles({"runners/typescript"}, Path("/checkout")), True)


class HelloProcess:
    """Answers every handshake like a runner named after the launch command."""

    def __init__(self, error: Exception | None = None, features: tuple[str, ...] = ()) -> None:
        self.error = error
        self.features = features
        self.requests: list[RunRequest] = []

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return RunReport(RunnerInfo(launch.command[0], 1, "9.9", self.features))

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        raise AssertionError("cstudy doctor never benches")

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        raise AssertionError("cstudy doctor never runs a suite")


@dataclass
class FakeCommands:
    results: dict[tuple[str, ...], ProbeResult | None] = field(default_factory=dict)
    ran: list[tuple[tuple[str, ...], Path]] = field(default_factory=list)
    environments: list[Mapping[str, str] | None] = field(default_factory=list)
    """The variables each command in `ran` was given on top of the process's own."""

    def run(
        self, command: Sequence[str], cwd: Path, environment: Mapping[str, str] | None = None
    ) -> ProbeResult | None:
        self.ran.append((tuple(command), cwd))
        self.environments.append(environment)
        return self.results.get(tuple(command), ProbeResult(0, ""))


@dataclass
class FakeSetup:
    missing: tuple[str, ...] = ()
    current: bool = True
    refreshed: list[Path] = field(default_factory=list[Path])

    def workspace_at_or_above(self, directory: Path) -> Path | None:
        return None

    def checkout_at_or_above(self, directory: Path) -> Path | None:
        return None

    def missing_files(self, root: Path) -> tuple[str, ...]:
        return self.missing

    def write_missing(self, root: Path) -> ScaffoldOutcome:
        return ScaffoldOutcome(self.missing, ())

    def runtime_current(self, root: Path) -> bool:
        return self.current

    def refresh_runtime(self, root: Path) -> None:
        self.refreshed.append(root)

    def init_git(self, root: Path) -> None:
        raise AssertionError("cstudy doctor never runs git init")


@dataclass
class FakeProjectLinks:
    unlinked_folders: tuple[str, ...] = ()
    moved: str | None = None
    relinked: list[Path] = field(default_factory=list[Path])

    def unlinked(self, root: Path) -> tuple[str, ...]:
        return self.unlinked_folders

    def relink(self, root: Path) -> tuple[str, ...]:
        self.relinked.append(root)
        return self.unlinked_folders

    def moved_venv(self, root: Path) -> str | None:
        return self.moved


LATEST_SCHEMA = 5


@dataclass
class FakeProgress:
    """A progress.db at `found` (None: not created yet) that migrates to `latest`."""

    found: int | None = LATEST_SCHEMA
    latest: int = LATEST_SCHEMA
    unreadable: str | None = None
    migration_error: str | None = None
    migrations: int = 0

    def schema(self) -> ProgressSchema:
        if self.unreadable:
            raise UsageError(self.unreadable)
        return ProgressSchema(self.found, self.latest)

    def migrate(self) -> None:
        if self.migration_error:
            raise UsageError(self.migration_error)
        self.migrations += 1
        self.found = self.latest


def healthy_runners() -> dict[Language, LanguageRunner]:
    return {
        language: FakeLanguageRunner(Prepared(RunnerLaunch((language.value,), Path("/"), 1000)))
        for language in Language
    }


HOMEBREW_INSTALL = Install(
    InstallKind.HOMEBREW,
    Path("/opt/homebrew/Cellar/cstudy/0.1.0/libexec"),
    Path("/opt/homebrew/bin/cstudy"),
    "0.1.0",
)
UV_INSTALL = Install(
    InstallKind.UV_TOOL,
    Path("/home/me/.local/share/uv/tools/coding-study"),
    Path("/home/me/.local/bin/cstudy"),
    "0.0.9",
)


@dataclass
class FakeInstalls:
    """One Homebrew install, which is also the running one, unless told otherwise."""

    on_path: tuple[Install, ...] = (HOMEBREW_INSTALL,)
    running: Install = HOMEBREW_INSTALL

    def scan(self) -> InstallScan:
        return InstallScan(self.on_path, self.running, Path("/home/me"))


def workspace_with(
    paths: set[str] | None = None,
    runners: dict[Language, LanguageRunner] | None = None,
    process: HelloProcess | None = None,
    commands: FakeCommands | None = None,
    setup: FakeSetup | None = None,
    links: FakeProjectLinks | None = None,
    progress: FakeProgress | None = None,
    preferences: MemoryPreferences | None = None,
    language_servers: FakeLanguageServers | None = None,
) -> PracticeWorkspace:
    servers = language_servers or FakeLanguageServers()
    return PracticeWorkspace(
        files=FakeFiles(set(COMPLETE_WORKSPACE) if paths is None else paths),
        created_with=RUNNING_VERSION,
        setup=setup or FakeSetup(),
        toolchains=FakeToolchains(healthy_runners() if runners is None else runners),
        runner_process=process or HelloProcess(),
        commands=commands or FakeCommands(),
        project_links=links or FakeProjectLinks(),
        progress=progress or FakeProgress(),
        preferences=preferences or MemoryPreferences(),
        language_servers=servers,
        language_server_installer=servers,
    )


def doctor(
    tools: FakeTools | None = None,
    config: FakeConfigSource | None = None,
    workspace: PracticeWorkspace | NotFound | None = None,
    content: ContentLocation | NotFound = BUNDLED,
    debug_servers: FakeDebugServers | None = None,
    web: WebUiInstall | None = None,
    jdk: FakeJdk | None = None,
    installs: FakeInstalls | None = None,
    sandbox: FakeSandbox | None = None,
) -> DoctorReport:
    return run_doctor(
        DoctorEnvironment(
            tools=tools or FakeTools(),
            jdk=jdk or FakeJdk(),
            debug_servers=debug_servers or FakeDebugServers(),
            config=config or FakeConfigSource(),
            content=content,
            workspace=workspace or workspace_with(),
            version=RUNNING_VERSION,
            web=web or FakeWebUi(),
            installs=installs or FakeInstalls(),
            sandbox=sandbox or FakeSandbox(),
        ),
        lambda _line: None,
    )


def check(report: DoctorReport, name: str) -> CheckResult:
    return next(result for result in report.results if result.name == name)


def summary(report: DoctorReport, name: str) -> tuple[CheckStatus, str]:
    result = check(report, name)
    return result.status, result.detail


def tools_with(command: tuple[str, ...], result: ProbeResult | None) -> FakeTools:
    tools = FakeTools()
    tools.outputs[command] = result
    return tools


def test_healthy_toolchain_reports_versions():
    report = doctor()
    assert [(r.name, r.status, r.detail) for r in report.results[:6]] == [
        ("python", OK, "3.13.2"),
        ("uv", OK, "0.10.11"),
        ("node", OK, "v24.18.0 (type stripping)"),
        ("pnpm", OK, "9.15.9"),
        ("java", OK, "25.0.5 (JAVA_HOME)"),
        ("gradle", OK, "9.8.2"),
    ]


def test_complete_setup_passes():
    assert doctor().passed is True


def test_node_older_than_24_fails():
    tools = tools_with(("node", "--version"), ProbeResult(0, "v22.11.0\n"))
    assert summary(doctor(tools), "node") == (
        FAIL,
        "v22.11.0 (need 24 or newer for type stripping)",
    )


@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        (SelectedJdk("21.0.13", 21, JdkSource.PATH), (OK, "21.0.13 (PATH)")),
        (SelectedJdk("26.0.1", 26, JdkSource.JAVA_HOME), (OK, "26.0.1 (JAVA_HOME)")),
        (
            SelectedJdk("27", 27, JdkSource.JAVA_HOME),
            (FAIL, "27 (not supported yet: cstudy supports JDK 21 to 26)"),
        ),
        (
            SelectedJdk("17.0.9", 17, JdkSource.PATH),
            (FAIL, "17.0.9 (too old: cstudy supports JDK 21 to 26)"),
        ),
        (None, (FAIL, "not found")),
    ],
    ids=["21", "26", "27", "17", "none"],
)
def test_the_java_row_checks_the_selected_jdk_against_the_supported_range(selected, expected):
    assert summary(doctor(jdk=FakeJdk(selected)), "java") == expected


def test_a_java_home_without_a_jdk_fails_the_java_row():
    jdk = FakeJdk(None, java_home_without_jdk="/opt/jdk")
    assert summary(doctor(jdk=jdk), "java") == (FAIL, "JAVA_HOME (/opt/jdk) holds no JDK")


@pytest.mark.parametrize(
    "jdk",
    [
        FakeJdk(SelectedJdk("27", 27, JdkSource.JAVA_HOME)),
        FakeJdk(SelectedJdk("17.0.9", 17, JdkSource.PATH)),
        FakeJdk(None),
        FakeJdk(None, java_home_without_jdk="/opt/jdk"),
    ],
    ids=["27", "17", "none", "bad JAVA_HOME"],
)
def test_a_failing_java_row_says_how_to_select_a_supported_jdk(jdk):
    assert check(doctor(jdk=jdk), "java").fix == SELECT_A_JDK


def test_the_fix_names_the_toolchains_guides_jdk_section():
    assert JDK_FIX == SELECT_A_JDK


def test_a_supported_jdk_needs_no_fix():
    assert check(doctor(), "java").fix is None


def test_missing_tool_fails_with_fix():
    result = check(doctor(tools_with(("pnpm", "--version"), None)), "pnpm")
    assert (result.status, result.detail, result.fix) == (
        FAIL,
        "not found on PATH",
        f"install pnpm: {TOOLCHAINS_GUIDE}#nodejs-and-pnpm",
    )


@pytest.mark.parametrize(
    ("command", "name", "fix"),
    [
        (("uv", "--version"), "uv", f"install uv: {TOOLCHAINS_GUIDE}#python-and-uv"),
        (
            ("uv", "python", "find", "3.13"),
            "python",
            f"install uv: {TOOLCHAINS_GUIDE}#python-and-uv",
        ),
        (
            ("node", "--version"),
            "node",
            f"install Node 24 or newer: {TOOLCHAINS_GUIDE}#nodejs-and-pnpm",
        ),
    ],
)
def test_missing_toolchain_fix_links_its_install_guide(command, name, fix):
    assert check(doctor(tools_with(command, None)), name).fix == fix


def test_failing_version_command_fails():
    tools = tools_with(("node", "--version"), ProbeResult(1, "dyld: library not loaded"))
    assert summary(doctor(tools), "node") == (FAIL, "`node --version` exited with 1")


def test_unreadable_version_fails():
    tools = tools_with(("pnpm", "--version"), ProbeResult(0, "unknown"))
    assert summary(doctor(tools), "pnpm") == (FAIL, "`pnpm --version` printed no version")


def test_python_needs_uv():
    tools = tools_with(("uv", "python", "find", "3.13"), None)
    assert summary(doctor(tools), "python") == (FAIL, "uv not found (uv provides Python 3.13)")


def test_python_313_not_installed_fails_with_fix():
    tools = tools_with(("uv", "python", "find", "3.13"), ProbeResult(2, "error: not found"))
    result = check(doctor(tools), "python")
    assert (result.status, result.fix) == (FAIL, "uv python install 3.13")


def test_missing_gradle_is_only_a_warning():
    result = check(doctor(tools_with(("gradle", "--version"), None)), "gradle")
    assert (result.status, result.fix) == (WARN, "brew install gradle")


def test_healthy_optional_toolchains_report_versions():
    report = doctor()
    assert [(r.name, r.status, r.detail) for r in report.results[6:9]] == [
        ("go", OK, "1.25.0"),
        ("rustc", OK, "1.80.0"),
        ("cargo", OK, "1.80.0"),
    ]


@pytest.mark.parametrize(
    ("command", "name", "flag", "anchor"),
    [
        (("go", "version"), "go", "--lang go", "go"),
        (("rustc", "--version"), "rustc", "--lang rust", "rust"),
        (("cargo", "--version"), "cargo", "--lang rust", "rust"),
    ],
)
def test_missing_optional_toolchain_only_warns_and_links_its_install_guide(
    command, name, flag, anchor
):
    report = doctor(tools_with(command, None))
    result = check(report, name)
    assert (result.status, result.detail, report.passed) == (WARN, "not found on PATH", True)
    assert result.fix is not None
    assert result.fix.startswith(f"needed for {flag}")
    assert result.fix.endswith(f"{TOOLCHAINS_GUIDE}#{anchor}")


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("go version go1.25 linux/amd64", OK),
        ("go version go1.25.0 linux/amd64", OK),
        ("go version go1.26rc1 linux/amd64", OK),
        ("go version devel go1.26-abc123 Mon Jan 1 00:00:00 2026 darwin/arm64", OK),
        ("go version go1.24.13 linux/arm64", WARN),
        ("go version go1.23.9 darwin/arm64", WARN),
        ("go version go1.9.7 linux/amd64", WARN),
    ],
)
def test_go_must_be_1_25_or_newer(output, expected):
    tools = tools_with(("go", "version"), ProbeResult(0, output))
    assert check(doctor(tools), "go").status is expected


def test_old_go_says_cstudy_never_downloads_a_toolchain():
    tools = tools_with(("go", "version"), ProbeResult(0, "go version go1.24.13 darwin/arm64"))
    assert summary(doctor(tools), "go") == (
        WARN,
        "1.24.13 (need 1.25 or newer; "
        "cstudy builds with GOTOOLCHAIN=local and never downloads one)",
    )


@pytest.mark.parametrize(
    "probe", [None, ProbeResult(0, "go version go1.24.13 darwin/arm64")], ids=["missing", "old"]
)
def test_the_go_fix_asks_for_go_1_25(probe):
    tools = tools_with(("go", "version"), probe)
    assert check(doctor(tools), "go").fix == (
        f"needed for --lang go, install Go 1.25 or newer: {TOOLCHAINS_GUIDE}#go"
    )


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("rustc 1.80.0 (051478957 2024-07-21)", OK),
        ("rustc 1.100.2 (abcdef012 2027-01-01)", OK),
        ("rustc 1.83.0-nightly (c273 2024-10-01)", OK),
        ("rustc 1.79.0 (129f3b996 2024-06-10)", WARN),
        ("rustc 1.8.0 (db2d3f84d 2016-04-12)", WARN),
    ],
)
def test_rustc_must_be_1_80_or_newer(output, expected):
    tools = tools_with(("rustc", "--version"), ProbeResult(0, output))
    result = check(doctor(tools), "rustc")
    assert result.status is expected


def test_old_rustc_names_the_minimum_and_the_guide():
    tools = tools_with(
        ("rustc", "--version"), ProbeResult(0, "rustc 1.79.0 (129f3b996 2024-06-10)")
    )
    result = check(doctor(tools), "rustc")
    assert (result.detail, result.fix) == (
        "1.79.0 (need 1.80 or newer)",
        f"needed for --lang rust, install Rust 1.80 or newer with rustup: {TOOLCHAINS_GUIDE}#rust",
    )


def test_installed_debuggers_pass_with_delves_version_and_the_servers_path():
    report = doctor()
    assert (summary(report, "dlv"), summary(report, "debugserver")) == (
        (OK, "1.27.2"),
        (OK, "/xcode/debugserver"),
    )


def test_another_delve_release_passes_and_names_the_tested_one():
    tools = tools_with(DELVE_VERSION, ProbeResult(0, "Delve Debugger\nVersion: 1.26.1\n"))
    assert summary(doctor(tools), "dlv") == (OK, "1.26.1 (cstudy is tested with 1.27.2)")


GO_VERSION = ("go", "version")


def test_a_delve_that_refuses_the_installed_go_warns_with_the_go_to_install():
    tools = tools_with(GO_VERSION, ProbeResult(0, "go version go1.24.13 linux/arm64\n"))
    result = check(doctor(tools), "dlv")
    assert (result.status, result.detail, result.fix) == (
        WARN,
        "1.27.2 (debugs only Go 1.25 or newer; found Go 1.24.13)",
        f"needed for --debug with --lang go, install Go 1.25 or newer: {TOOLCHAINS_GUIDE}#go",
    )


def test_a_delve_that_refuses_the_installed_go_does_not_fail_the_report():
    tools = tools_with(GO_VERSION, ProbeResult(0, "go version go1.24.13 linux/arm64\n"))
    assert doctor(tools).passed


def test_a_go_the_delve_accepts_passes():
    tools = tools_with(GO_VERSION, ProbeResult(0, "go version go1.25 linux/amd64\n"))
    assert summary(doctor(tools), "dlv") == (OK, "1.27.2")


def test_an_older_delve_is_not_judged_against_the_go_it_may_accept():
    tools = FakeTools()
    tools.outputs[GO_VERSION] = ProbeResult(0, "go version go1.24.13 linux/arm64\n")
    tools.outputs[DELVE_VERSION] = ProbeResult(0, "Delve Debugger\nVersion: 1.26.1\n")
    assert summary(doctor(tools), "dlv") == (OK, "1.26.1 (cstudy is tested with 1.27.2)")


def test_a_missing_go_leaves_the_delve_row_to_the_go_row():
    tools = tools_with(GO_VERSION, None)
    assert summary(doctor(tools), "dlv") == (OK, "1.27.2")


@pytest.mark.parametrize(
    ("servers", "name", "fix"),
    [
        (
            FakeDebugServers(delve_server=replace(DELVE, path=None)),
            "dlv",
            f"needed for --debug with --lang go, run `go install dlv`: {TOOLCHAINS_GUIDE}#go",
        ),
        (
            FakeDebugServers(lldb=replace(DEBUGSERVER, path=None)),
            "debugserver",
            "needed for --debug with --lang rust, run `xcode-select --install`: "
            f"{TOOLCHAINS_GUIDE}#rust",
        ),
        (
            FakeDebugServers(lldb=DebugServer("lldb-server", "install your lldb package")),
            "lldb-server",
            "needed for --debug with --lang rust, install your lldb package: "
            f"{TOOLCHAINS_GUIDE}#rust",
        ),
    ],
)
def test_a_missing_debugger_only_warns_with_how_to_install_it(servers, name, fix):
    report = doctor(debug_servers=servers)
    result = check(report, name)
    assert (result.status, result.detail, result.fix, report.passed) == (
        WARN,
        "not found",
        fix,
        True,
    )


def test_a_delve_that_does_not_run_only_warns():
    tools = tools_with(DELVE_VERSION, ProbeResult(1, "killed"))
    assert summary(doctor(tools), "dlv") == (WARN, "`/go/bin/dlv version` exited with 1")


def test_a_rustup_shim_without_a_toolchain_only_warns():
    tools = tools_with(("rustc", "--version"), ProbeResult(1, "error: no default toolchain"))
    assert summary(doctor(tools), "rustc") == (WARN, "`rustc --version` exited with 1")


def test_missing_optional_toolchains_do_not_change_the_core_checks():
    tools = FakeTools()
    for command in (("go", "version"), ("rustc", "--version"), ("cargo", "--version")):
        tools.outputs[command] = None
    report = doctor(tools)
    assert [r.status for r in report.results if r.name in {"python", "uv", "node", "java"}] == [
        OK
    ] * 4


def test_missing_config_file_uses_defaults():
    assert summary(doctor(), "config") == (
        OK,
        "/home/user/.config/coding-study/config.toml (not found, using defaults)",
    )


def test_valid_config_file_passes():
    config = FakeConfigSource(present=True)
    assert summary(doctor(config=config), "config") == (OK, config.location)


def test_invalid_config_file_fails_with_its_issues():
    config = FakeConfigSource(present=True, issues=("bench.reps: expected a positive integer",))
    assert summary(doctor(config=config), "config") == (
        FAIL,
        f"{config.location}: bench.reps: expected a positive integer",
    )


def test_bundled_content_is_reported():
    assert summary(doctor(), "content") == (OK, "/tool/content (bundled)")


def test_checkout_content_is_reported():
    assert summary(doctor(content=CHECKOUT), "content") == (OK, "/checkout (checkout)")


def test_missing_content_fails():
    report = doctor(content=NotFound("no content bundled"))
    assert summary(report, "content") == (FAIL, "no content bundled")


def test_missing_workspace_is_a_single_warning_pointing_at_cs_init():
    report = doctor(workspace=NotFound("no coding-study workspace at /tmp"))
    assert [(r.name, r.status, r.fix) for r in report.results if r.name == "workspace"] == [
        ("workspace", WARN, "cstudy init")
    ]
    assert report.results[-1].name == "workspace"


def test_a_workspace_this_cs_cannot_use_fails():
    unusable = NotFound("the workspace at /ws uses schema 2: upgrade cstudy", unusable=True)
    result = check(doctor(workspace=unusable), "workspace")
    assert (result.status, result.detail, result.fix) == (FAIL, unusable.reason, None)


def test_workspace_is_reported_with_the_version_that_created_it():
    assert summary(doctor(), "workspace") == (OK, "/ws (created with cstudy 0.1.0)")


def test_a_workspace_from_another_version_names_both():
    workspace = replace(workspace_with(), created_with="0.0.9")
    assert summary(doctor(workspace=workspace), "workspace") == (
        OK,
        "/ws (created with cstudy 0.0.9, running 0.1.0)",
    )


def test_a_complete_workspace_passes_the_files_check():
    assert summary(doctor(), "workspace files") == (OK, "")


def test_missing_template_files_fail_with_the_fix_command():
    setup = FakeSetup(missing=("jvm/settings.gradle.kts",))
    result = check(doctor(workspace=workspace_with(setup=setup)), "workspace files")
    assert (result.status, result.detail, result.fix) == (
        FAIL,
        "1 missing: jvm/settings.gradle.kts",
        "cstudy doctor --fix",
    )


GO_RUST_FILES = ("go.work", "go/go.mod", "go/practice/.gitkeep", "rust/Cargo.toml", "rust/lib.rs")


def test_missing_go_and_rust_files_do_not_fail_the_files_check():
    setup = FakeSetup(missing=GO_RUST_FILES)
    report = doctor(workspace=workspace_with(setup=setup))
    assert summary(report, "workspace files") == (OK, "")
    assert report.passed is True


def test_missing_go_and_rust_files_warn_with_the_fix_command():
    setup = FakeSetup(missing=GO_RUST_FILES)
    result = check(doctor(workspace=workspace_with(setup=setup)), "go and rust files")
    assert (result.status, result.detail, result.fix) == (
        WARN,
        "5 missing: go.work, go/go.mod, go/practice/.gitkeep, rust/Cargo.toml, rust/lib.rs",
        "cstudy doctor --fix",
    )


def test_a_workspace_with_the_go_and_rust_files_passes_their_check():
    assert summary(doctor(), "go and rust files") == (OK, "")


def test_core_files_still_fail_when_go_and_rust_files_are_missing_too():
    setup = FakeSetup(
        missing=("go.work", "jvm/gradlew", "rust/Cargo.toml", "python/pyproject.toml")
    )
    report = doctor(workspace=workspace_with(setup=setup))
    assert summary(report, "workspace files") == (
        FAIL,
        "2 missing: jvm/gradlew, python/pyproject.toml",
    )
    assert summary(report, "go and rust files")[0] is WARN
    assert report.passed is False


def test_many_missing_files_are_summarized():
    setup = FakeSetup(missing=tuple(f"f{index}" for index in range(7)))
    detail = check(doctor(workspace=workspace_with(setup=setup)), "workspace files").detail
    assert detail == "7 missing: f0, f1, f2, f3, f4 and 2 more"


def test_a_workspace_with_a_projects_folder_passes_its_check():
    assert summary(doctor(), "projects") == (OK, "")


def test_a_workspace_without_a_projects_folder_only_warns_with_the_fix_command():
    paths = COMPLETE_WORKSPACE - {"projects"}
    result = check(doctor(workspace=workspace_with(paths)), "projects")
    assert (result.status, result.detail, result.fix) == (
        WARN,
        "missing (a workspace from before project problems)",
        "cstudy doctor --fix",
    )


def test_a_missing_projects_folder_does_not_fail_the_files_check():
    setup = FakeSetup(missing=("projects/.gitkeep",))
    report = doctor(workspace=workspace_with(COMPLETE_WORKSPACE - {"projects"}, setup=setup))
    assert (summary(report, "workspace files"), report.passed) == ((OK, ""), True)


def test_the_files_check_leaves_the_projects_folder_to_its_own_check():
    setup = FakeSetup(missing=("projects/.gitkeep", "python/pyproject.toml"))
    report = doctor(workspace=workspace_with(setup=setup))
    assert summary(report, "workspace files") == (FAIL, "1 missing: python/pyproject.toml")


def test_project_folders_linked_to_the_workspace_venv_pass():
    assert summary(doctor(), "project links") == (OK, "")


def test_unlinked_project_folders_only_warn_listing_them_with_the_fix_command():
    links = FakeProjectLinks(("projects/bank-project-python", "projects/parking-lot-python"))
    report = doctor(workspace=workspace_with(links=links))
    result = check(report, "project links")
    assert (result.status, result.detail, result.fix, report.passed) == (
        WARN,
        "2 missing or dangling .venv links: projects/bank-project-python, "
        "projects/parking-lot-python",
        "cstudy doctor --fix",
        True,
    )


def test_many_unlinked_project_folders_are_summarized():
    links = FakeProjectLinks(tuple(f"projects/p{index}" for index in range(6)))
    detail = check(doctor(workspace=workspace_with(links=links)), "project links").detail
    assert detail == (
        "6 missing or dangling .venv links: projects/p0, projects/p1, projects/p2, projects/p3, "
        "projects/p4 and 1 more"
    )


def test_a_venv_whose_scripts_name_this_workspace_passes():
    assert summary(doctor(), "python/.venv location") == (OK, "")


def test_a_venv_from_before_the_workspace_moved_only_warns_with_the_fix_command():
    links = FakeProjectLinks(moved="/old/ws/python/.venv")
    report = doctor(workspace=workspace_with(links=links))
    result = check(report, "python/.venv location")
    assert (result.status, result.detail, result.fix, report.passed) == (
        WARN,
        "its console scripts name /old/ws/python/.venv: the workspace moved, so they no "
        "longer run (cstudy still does)",
        "rm -rf python/.venv && cstudy doctor --fix",
        True,
    )


def test_the_venv_location_is_not_checked_before_the_venv_exists():
    report = doctor(workspace=workspace_with(COMPLETE_WORKSPACE - {"python/.venv"}))
    assert "python/.venv location" not in [result.name for result in report.results]


def test_pytest_in_the_workspace_venv_passes():
    assert summary(doctor(), "python pytest") == (OK, "installed (Python project problems)")


def test_missing_pytest_is_only_a_warning_with_the_fix():
    report = doctor(tools_with(IMPORT_PYTEST, ProbeResult(1, "ModuleNotFoundError")))
    result = check(report, "python pytest")
    assert (result.status, result.detail, result.fix, report.passed) == (
        WARN,
        "not installed (only Python project problems need it)",
        "cstudy doctor --fix",
        True,
    )


def test_pytest_is_not_checked_before_the_venv_exists():
    report = doctor(workspace=workspace_with(COMPLETE_WORKSPACE - {"python/.venv"}))
    assert "python pytest" not in [result.name for result in report.results]


def test_project_rows_follow_the_workspace_files_in_the_specs_order():
    names = [result.name for result in doctor().results]
    rows = ["projects", "python pytest", "project links", "python/.venv location"]
    assert [name for name in names if name in rows] == rows


def test_repair_recreates_the_project_links():
    links = FakeProjectLinks(("projects/bank-project-python",))
    repair_workspace(workspace_with(links=links), lambda _line: None)
    assert links.relinked == [Path("/ws")]


def test_repair_names_each_relinked_folder():
    lines: list[str] = []
    links = FakeProjectLinks(("projects/bank-project-python",))
    repair_workspace(workspace_with(links=links), lines.append)
    assert "relinked projects/bank-project-python/.venv" in lines


def test_a_current_runner_runtime_passes():
    assert summary(doctor(), "runner runtime") == (OK, "matches the content")


def test_a_stale_runner_runtime_fails_with_the_fix_command():
    setup = FakeSetup(current=False)
    result = check(doctor(workspace=workspace_with(setup=setup)), "runner runtime")
    assert (result.status, result.fix) == (FAIL, "cstudy doctor --fix")


def test_a_current_progress_database_passes():
    assert summary(doctor(), "progress database") == (OK, "schema 5")


def test_a_progress_database_not_created_yet_passes():
    workspace = workspace_with(progress=FakeProgress(found=None))
    assert summary(doctor(workspace=workspace), "progress database") == (
        OK,
        "not created yet (created on first use)",
    )


def test_an_older_progress_database_only_warns_that_it_migrates_on_next_use():
    report = doctor(workspace=workspace_with(progress=FakeProgress(found=4)))
    result = check(report, "progress database")
    assert (result.status, result.detail, result.fix, report.passed) == (
        WARN,
        "schema 4, this cstudy uses 5: migrates on next use; `--fix` migrates now",
        "cstudy doctor --fix",
        True,
    )


def test_a_progress_database_without_a_schema_is_older_than_the_first():
    report = doctor(workspace=workspace_with(progress=FakeProgress(found=0)))
    assert check(report, "progress database").status is WARN


def test_a_newer_progress_database_fails_telling_to_upgrade_cstudy():
    report = doctor(workspace=workspace_with(progress=FakeProgress(found=6)))
    result = check(report, "progress database")
    assert (result.status, result.detail, result.fix, report.passed) == (
        FAIL,
        "schema 6 is newer than the 5 this cstudy reads",
        "upgrade cstudy",
        False,
    )


def test_an_unreadable_progress_database_fails_with_the_reason():
    progress = FakeProgress(unreadable="the progress database cannot be read: not a database")
    report = doctor(workspace=workspace_with(progress=progress))
    result = check(report, "progress database")
    assert (result.status, result.detail) == (
        FAIL,
        "the progress database cannot be read: not a database",
    )


def test_the_progress_database_row_follows_the_runner_runtime():
    names = [result.name for result in doctor().results]
    assert names.index("progress database") == names.index("runner runtime") + 1


def test_repair_migrates_an_older_progress_database():
    progress = FakeProgress(found=4)
    repair_workspace(workspace_with(progress=progress), lambda _line: None)
    assert progress.migrations == 1


def test_repair_names_the_migration():
    lines: list[str] = []
    repair_workspace(workspace_with(progress=FakeProgress(found=4)), lines.append)
    assert lines == ["migrated progress.db from schema 4 to 5"]


@pytest.mark.parametrize("found", [LATEST_SCHEMA, None, 6])
def test_repair_leaves_a_progress_database_that_is_current_absent_or_newer(found):
    progress = FakeProgress(found=found)
    repair_workspace(workspace_with(progress=progress), lambda _line: None)
    assert progress.migrations == 0


def test_repair_survives_an_unreadable_progress_database():
    progress = FakeProgress(unreadable="the progress database cannot be read: not a database")
    repair_workspace(workspace_with(progress=progress), lambda _line: None)
    assert progress.migrations == 0


def test_repair_says_why_a_progress_database_stays_as_it_is():
    lines: list[str] = []
    progress = FakeProgress(unreadable="the progress database cannot be read: not a database")
    repair_workspace(workspace_with(progress=progress), lines.append)
    assert lines == [
        "progress.db stays as it is: the progress database cannot be read: not a database"
    ]


def test_repair_survives_a_migration_that_fails():
    lines: list[str] = []
    progress = FakeProgress(found=4, migration_error="the progress database is locked")
    repair_workspace(workspace_with(progress=progress), lines.append)
    assert lines == ["progress.db stays as it is: the progress database is locked"]


def test_repair_writes_the_missing_files():
    setup = FakeSetup(missing=("python/pyproject.toml",))
    restored = repair_workspace(workspace_with(setup=setup), lambda _line: None)
    assert restored.written == ("python/pyproject.toml",)


def test_repair_names_each_restored_file():
    lines: list[str] = []
    repair_workspace(workspace_with(setup=FakeSetup(missing=("jvm/gradlew",))), lines.append)
    assert lines == ["restored jvm/gradlew"]


def test_repair_refreshes_the_runner_runtime():
    setup = FakeSetup()
    repair_workspace(workspace_with(setup=setup), lambda _line: None)
    assert setup.refreshed == [Path("/ws")]


def test_workspace_project_not_set_up_yet_is_a_warning():
    report = doctor(workspace=workspace_with(paths=set()))
    assert summary(report, "python/.venv") == (WARN, "not set up yet (no python)")


def test_workspace_artifact_present_passes():
    assert summary(doctor(), "typescript/node_modules") == (OK, "")


@pytest.mark.parametrize("artifact", ["python/.venv", "typescript/node_modules"])
def test_missing_workspace_artifact_fails_with_the_fix_command(artifact):
    report = doctor(workspace=workspace_with(paths=COMPLETE_WORKSPACE - {artifact}))
    result = check(report, artifact)
    assert (result.status, result.detail, result.fix) == (FAIL, "missing", "cstudy doctor --fix")


def test_debugpy_in_the_workspace_venv_passes():
    assert summary(doctor(), "python debugpy") == (OK, "installed (cstudy test --debug)")


@pytest.mark.parametrize("probe", [ProbeResult(1, "ModuleNotFoundError: debugpy"), None])
def test_missing_debugpy_is_only_a_warning_with_the_fix(probe):
    result = check(doctor(tools_with(IMPORT_DEBUGPY, probe)), "python debugpy")
    assert (result.status, result.detail, result.fix) == (
        WARN,
        "not installed (only cstudy test --debug needs it)",
        "uv add --dev debugpy --directory python",
    )


def test_missing_debugpy_does_not_fail_the_report():
    probe = ProbeResult(1, "ModuleNotFoundError: debugpy")
    assert doctor(tools_with(IMPORT_DEBUGPY, probe)).passed is True


def test_debugpy_is_not_checked_before_the_venv_exists():
    report = doctor(workspace=workspace_with(paths=COMPLETE_WORKSPACE - {"python/.venv"}))
    assert "python debugpy" not in [result.name for result in report.results]


def test_missing_gradle_wrapper_fails_with_how_to_generate_it():
    report = doctor(workspace=workspace_with(paths=COMPLETE_WORKSPACE - {"jvm/gradlew"}))
    result = check(report, "jvm/gradlew")
    assert (result.status, result.fix) == (FAIL, "gradle wrapper (in jvm)")


def test_every_core_language_runner_is_checked():
    names = [
        r.name
        for r in doctor().results
        if r.name.startswith("runner ") and r.name != "runner runtime"
    ]
    assert names == ["runner python", "runner typescript", "runner java", "runner kotlin"]


def test_optional_language_runners_are_not_handshaken():
    report = doctor()
    assert {"runner go", "runner rust"}.isdisjoint(result.name for result in report.results)


def test_runner_that_answers_hello_passes_with_its_runtime():
    assert summary(doctor(), "runner java") == (OK, "answers hello: java 9.9, protocol 1")


def test_runner_features_follow_the_protocol():
    report = doctor(workspace=workspace_with(process=HelloProcess(features=("stress",))))
    assert summary(report, "runner java") == (OK, "answers hello: java 9.9, protocol 1, stress")


def test_handshake_prepares_a_problem_with_no_user_code():
    runners = healthy_runners()
    doctor(workspace=workspace_with(runners=runners))
    kotlin = runners[Language.KOTLIN]
    assert isinstance(kotlin, FakeLanguageRunner)
    assert kotlin.scopes == [UserCode(HANDSHAKE_META)]


def test_handshake_sends_no_jobs():
    process = HelloProcess()
    doctor(workspace=workspace_with(process=process))
    assert {request.jobs for request in process.requests} == {()}


@pytest.mark.parametrize(
    "error",
    [RunnerStartError("runner did not say hello within 5000 ms"), RunnerProtocolError("bad event")],
)
def test_runner_that_does_not_answer_fails_with_the_fix_command(error):
    result = check(doctor(workspace=workspace_with(process=HelloProcess(error))), "runner python")
    assert (result.status, result.detail, result.fix) == (FAIL, str(error), "cstudy doctor --fix")


def test_runner_that_does_not_build_fails_with_the_compiler_output():
    runners = healthy_runners()
    runners[Language.JAVA] = FakeLanguageRunner(BuildFailed(("Main.java:3: error: oops",)))
    result = check(doctor(workspace=workspace_with(runners=runners)), "runner java")
    assert (result.status, result.detail) == (FAIL, "does not build: Main.java:3: error: oops")


def test_only_the_first_line_of_a_start_error_is_shown():
    error = RunnerStartError("gradle build failed with exit code 1", ["line 1", "line 2"])
    result = check(doctor(workspace=workspace_with(process=HelloProcess(error))), "runner kotlin")
    assert result.detail == "gradle build failed with exit code 1"


def test_warnings_alone_still_pass():
    assert doctor(workspace=workspace_with(paths=set())).passed is True


def fix(
    workspace: PracticeWorkspace,
    content: ContentLocation | NotFound = BUNDLED,
    notify: Callable[[str], None] = lambda _line: None,
    jdk: FakeJdk | None = None,
):
    return fix_workspace(workspace, content, jdk or FakeJdk(), notify)


def test_fix_runs_the_setup_command_of_every_workspace_project():
    commands = FakeCommands()
    fix(workspace_with(commands=commands))
    assert commands.ran == [
        (("uv", "sync"), Path("/ws/python")),
        IMPORT_PYTEST_IN_PYTHON,
        (("pnpm", "install"), Path("/ws/typescript")),
        (
            (
                "./gradlew",
                f"-Dorg.gradle.java.home={JDK_HOME}",
                "--no-watch-fs",
                ":java:csClasspath",
                ":kotlin:csClasspath",
                "-Pcs.only=cs_doctor_handshake",
            ),
            Path("/ws/jvm"),
        ),
        *((on_jdk(step.command), Path("/ws/jvm")) for step in JVM_PROJECT_WARMUPS),
    ]


@pytest.mark.parametrize("language", ["java", "kotlin"])
def test_the_jvm_warm_up_builds_a_project_folder_per_language(language):
    """Project folders build offline on JUnit and kotlin-test, which no single-file problem
    needs, so a warm-up project of each language caches them."""
    commands = {step.command for step in JVM_PROJECT_WARMUPS}
    warmup = f"../.cs/runtime/runners/jvm/project-warmup/{language}"
    assert (
        "./gradlew",
        "-p",
        warmup,
        "-q",
        "--console=plain",
        "--no-watch-fs",
        "csClasspath",
    ) in commands


def test_the_jvm_warm_up_resolves_the_runtime_classpath():
    """Compiling classes alone never caches the runner's own libraries, so nothing would build
    offline afterwards (NFR-6)."""
    assert {":java:csClasspath", ":kotlin:csClasspath"} <= set(JVM_FIX.command)


def test_fix_installs_the_typescript_runner_of_a_content_checkout():
    commands = FakeCommands()
    fix(workspace_with(commands=commands), CHECKOUT)
    assert commands.ran[3] == (("pnpm", "install"), Path("/checkout/runners/typescript"))


def test_fix_skips_projects_that_are_not_set_up():
    commands = FakeCommands()
    fix(workspace_with(paths={"python"}, commands=commands))
    assert [command for command, _cwd in commands.ran] == [
        ("uv", "sync"),
        IMPORT_PYTEST_IN_PYTHON[0],
    ]


def test_fix_reports_each_command_outcome():
    commands = FakeCommands({("pnpm", "install"): ProbeResult(1, "ERR_PNPM_FETCH\n")})
    outcomes = fix(workspace_with(commands=commands), CHECKOUT)
    assert [(outcome.step.project, outcome.succeeded) for outcome in outcomes] == [
        ("python", True),
        ("typescript", False),
        ("runners/typescript", False),
        ("jvm", True),
        ("jvm", True),
        ("jvm", True),
    ]


def gradle_commands(commands: FakeCommands) -> list[tuple[str, ...]]:
    return [command for command, _cwd in commands.ran if command[0] == "./gradlew"]


def on_jdk(command: tuple[str, ...], home: Path = JDK_HOME) -> tuple[str, ...]:
    """`command`, a Gradle wrapper call, as it runs on the JDK at `home`."""
    return (command[0], f"-Dorg.gradle.java.home={home}", *command[1:])


@pytest.mark.parametrize(
    "jdk",
    [
        FakeJdk(None),
        FakeJdk(None, java_home_without_jdk="/opt/jdk"),
        FakeJdk(SelectedJdk("17.0.9", 17, JdkSource.PATH)),
    ],
    ids=["no JDK", "a JAVA_HOME without a JDK", "a JDK older than 21"],
)
def test_fix_skips_the_gradle_warm_up_without_a_jdk_it_can_build_with(jdk):
    commands = FakeCommands()
    fix(workspace_with(paths={"jvm"}, commands=commands), jdk=jdk)
    assert gradle_commands(commands) == []


@pytest.mark.parametrize(
    "selected",
    [
        SelectedJdk("21.0.13", 21, JdkSource.PATH),
        SelectedJdk("26.0.1", 26, JdkSource.JAVA_HOME),
        SelectedJdk("27", 27, JdkSource.JAVA_HOME),
    ],
    ids=["21", "26", "27, above the range"],
)
def test_fix_warms_up_gradle_on_any_jdk_it_can_build_with(selected):
    commands = FakeCommands()
    fix(workspace_with(paths={"jvm"}, commands=commands), jdk=FakeJdk(selected))
    assert gradle_commands(commands) == [
        on_jdk(step.command) for step in (JVM_FIX, *JVM_PROJECT_WARMUPS)
    ]


WARM_UP_STEPS = (JVM_FIX, *JVM_PROJECT_WARMUPS)


@pytest.mark.parametrize("step", WARM_UP_STEPS, ids=lambda step: step.command[-1])
def test_the_warm_up_rereads_the_runtime_it_just_refreshed(step):
    assert "--no-watch-fs" in step.command


JDK_26 = SelectedJdk("26.0.2", 26, JdkSource.JAVA_HOME)
HOME_26 = Path("/opt/jdks/26")


def warm_up_on_jdk_26() -> FakeCommands:
    commands = FakeCommands()
    fix(workspace_with(paths={"jvm"}, commands=commands), jdk=FakeJdk(JDK_26, home=HOME_26))
    return commands


def test_every_gradle_command_of_the_warm_up_names_the_selected_jdk():
    """One JDK per command: `-Dorg.gradle.java.home` outranks a setting in the Gradle home."""
    assert gradle_commands(warm_up_on_jdk_26()) == [
        on_jdk(step.command, HOME_26) for step in WARM_UP_STEPS
    ]


def test_every_gradle_command_of_the_warm_up_runs_with_java_home_set_to_it():
    commands = warm_up_on_jdk_26()
    assert commands.environments == [{"JAVA_HOME": str(HOME_26)}] * len(WARM_UP_STEPS)


def test_the_other_setup_commands_run_unchanged_and_in_the_process_environment():
    commands = FakeCommands()
    fix(workspace_with(paths={"python", "typescript"}, commands=commands))
    assert commands.environments == [None] * len(commands.ran)
    assert [command for command, _cwd in commands.ran][:2] == [
        ("uv", "sync"),
        IMPORT_PYTEST_IN_PYTHON[0],
    ]


def test_fix_reports_the_warm_up_skipped_for_want_of_a_jdk():
    outcome = fix(workspace_with(paths={"jvm"}), jdk=FakeJdk(None))[-1]
    assert (outcome.succeeded, outcome.detail, outcome.step.manual) == (
        False,
        "skipped: java is not installed or does not run",
        SELECT_A_JDK,
    )


def test_fix_reports_the_warm_up_skipped_for_a_jdk_too_old():
    jdk = FakeJdk(SelectedJdk("17.0.9", 17, JdkSource.PATH))
    outcome = fix(workspace_with(paths={"jvm"}), jdk=jdk)[-1]
    assert (outcome.succeeded, outcome.detail, outcome.step.manual) == (
        False,
        "skipped: JDK 17 is older than 21",
        SELECT_A_JDK,
    )


def test_fix_still_sets_up_the_other_projects_without_a_jdk():
    outcomes = fix(workspace_with(commands=FakeCommands()), jdk=FakeJdk(None))
    assert [(outcome.step.project, outcome.succeeded) for outcome in outcomes] == [
        ("python", True),
        ("typescript", True),
        ("jvm", False),
    ]


def test_fix_looks_for_a_jdk_only_in_a_workspace_with_a_jvm_project():
    jdk = FakeJdk()
    fix(workspace_with(paths={"python"}), jdk=jdk)
    assert jdk.asked == 0


def test_fix_with_a_missing_tool_fails_that_step():
    commands = FakeCommands({("uv", "sync"): None})
    outcomes = fix(workspace_with(commands=commands))
    assert outcomes[0].detail == "uv not found on PATH"


def pytest_missing() -> dict[tuple[str, ...], ProbeResult | None]:
    return {IMPORT_PYTEST_IN_PYTHON[0]: ProbeResult(1, "ModuleNotFoundError: pytest")}


def test_fix_adds_pytest_to_a_workspace_that_lacks_it_offline_first():
    commands = FakeCommands(pytest_missing())
    outcomes = fix(workspace_with(paths={"python"}, commands=commands))
    assert [command for command, _cwd in commands.ran] == [
        ("uv", "sync"),
        IMPORT_PYTEST_IN_PYTHON[0],
        ADD_PYTEST_OFFLINE,
    ]
    assert all(outcome.succeeded for outcome in outcomes)


def test_fix_adds_pytest_in_the_python_project():
    commands = FakeCommands(pytest_missing())
    fix(workspace_with(paths={"python"}, commands=commands))
    assert commands.ran[-1] == (ADD_PYTEST_OFFLINE, Path("/ws/python"))


def test_fix_leaves_the_requirements_alone_when_pytest_imports():
    commands = FakeCommands()
    fix(workspace_with(paths={"python"}, commands=commands))
    assert not [command for command, _cwd in commands.ran if command[:2] == ("uv", "add")]


def test_fix_adds_pytest_online_when_uvs_cache_lacks_it():
    results = {**pytest_missing(), ADD_PYTEST_OFFLINE: ProbeResult(2, "pytest not in the cache")}
    commands = FakeCommands(results)
    outcomes = fix(workspace_with(paths={"python"}, commands=commands))
    assert [command for command, _cwd in commands.ran][-2:] == [ADD_PYTEST_OFFLINE, ADD_PYTEST]
    assert outcomes[-1].succeeded


def test_fix_names_the_command_that_added_pytest_online():
    results = {**pytest_missing(), ADD_PYTEST_OFFLINE: ProbeResult(2, "")}
    outcomes = fix(workspace_with(paths={"python"}, commands=FakeCommands(results)))
    assert outcomes[-1].step.command == ADD_PYTEST


def test_fix_does_not_go_online_when_the_offline_add_worked():
    commands = FakeCommands(pytest_missing())
    fix(workspace_with(paths={"python"}, commands=commands))
    assert ADD_PYTEST not in [command for command, _cwd in commands.ran]


def test_fix_fails_the_pytest_step_with_the_manual_fix_when_offline_without_a_cache():
    results = {
        **pytest_missing(),
        ADD_PYTEST_OFFLINE: ProbeResult(2, "not in the cache"),
        ADD_PYTEST: ProbeResult(2, "error sending request"),
    }
    outcome = fix(workspace_with(paths={"python"}, commands=FakeCommands(results)))[-1]
    assert (outcome.succeeded, outcome.detail, outcome.step.manual) == (
        False,
        "exited with 2",
        'once online, run: uv add --dev "pytest>=9.1" --directory python',
    )


def commands_announced(lines: list[str]) -> list[str]:
    """The lines that announce a command, not the note of a step left out."""
    return [line for line in lines if line.startswith("running ")]


def test_fix_announces_each_attempt_to_add_pytest():
    lines: list[str] = []
    results = {**pytest_missing(), ADD_PYTEST_OFFLINE: ProbeResult(2, "")}
    fix(workspace_with(paths={"python"}, commands=FakeCommands(results)), notify=lines.append)
    assert commands_announced(lines)[1:] == [
        "running uv add --dev --offline pytest>=9.1 (in python)",
        "running uv add --dev pytest>=9.1 (in python)",
    ]


def test_fix_checks_pytest_only_in_workspaces_with_a_python_project():
    commands = FakeCommands(pytest_missing())
    fix(workspace_with(paths={"typescript"}, commands=commands))
    assert IMPORT_PYTEST_IN_PYTHON[0] not in [command for command, _cwd in commands.ran]


def test_the_pytest_requirement_is_the_one_the_template_declares():
    template = Path(__file__).parents[2] / "src/coding_study/adapters/workspace_template"
    declared = (template / "python" / "pyproject.toml").read_text(encoding="utf-8")
    assert f'"{PYTEST_REQUIREMENT}"' in declared


def test_a_step_without_a_manual_fix_has_none():
    assert FixStep("python", ("uv", "sync")).manual is None


def test_fix_announces_each_command_before_running_it():
    lines: list[str] = []
    fix(workspace_with(paths={"jvm"}), notify=lines.append)
    assert commands_announced(lines) == [
        "running ./gradlew --no-watch-fs :java:csClasspath :kotlin:csClasspath "
        "-Pcs.only=cs_doctor_handshake "
        "(in jvm)",
        *(f"running {step}" for step in JVM_PROJECT_WARMUPS),
    ]


def test_any_failure_fails_the_report():
    assert doctor(tools_with(("node", "--version"), None)).passed is False


@dataclass
class LibrariesRunner:
    """A JVM runner that says whether its project builds would find their libraries offline."""

    missing: str | None = None

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        return Prepared(RunnerLaunch(("java",), Path("/"), 1000))

    def uncached_project_libraries(self) -> str | None:
        return self.missing


def with_jvm_libraries(java: str | None, kotlin: str | None) -> PracticeWorkspace:
    runners = {
        **healthy_runners(),
        Language.JAVA: LibrariesRunner(java),
        Language.KOTLIN: LibrariesRunner(kotlin),
    }
    return workspace_with(runners=runners)


@pytest.mark.parametrize("language", ["java", "kotlin"])
def test_cached_project_libraries_pass(language):
    report = doctor(workspace=with_jvm_libraries(None, None))
    assert summary(report, f"{language} project libraries") == (
        CheckStatus.OK,
        f"cached ({language.capitalize()} project problems build offline)",
    )


def test_uncached_project_libraries_only_warn():
    """Only Java and Kotlin project problems need them."""
    report = doctor(workspace=with_jvm_libraries(None, "the warm-up project has not built"))
    result = check(report, "kotlin project libraries")
    assert (result.status, result.detail, result.fix) == (
        CheckStatus.WARN,
        "the warm-up project has not built",
        "cstudy doctor --fix",
    )


def test_a_runner_without_project_libraries_has_no_row():
    report = doctor()
    assert not [result for result in report.results if "project libraries" in result.name]


def test_project_libraries_are_not_checked_before_jvm_exists():
    runners = {**healthy_runners(), Language.JAVA: LibrariesRunner("not built")}
    paths = set(COMPLETE_WORKSPACE) - {"jvm"}
    report = doctor(workspace=workspace_with(paths=paths, runners=runners))
    assert not [result for result in report.results if "project libraries" in result.name]


# project folders a language checks (Rust: .cargo/config.toml and rust-analyzer's link)


@dataclass
class FolderCheckingRunner:
    """A runner whose project folders `cstudy doctor` checks and repairs."""

    checks: tuple[FolderCheck, ...]
    restored: tuple[str, ...] = ()
    repairs: int = 0

    def prepare(self, scope, notify):
        return Prepared(RunnerLaunch(("rust",), Path("/"), 1000))

    def folder_checks(self) -> tuple[FolderCheck, ...]:
        return self.checks

    def repair_folders(self) -> tuple[str, ...]:
        self.repairs += 1
        return self.restored


CONFIG_CHECK = FolderCheck("rust project config", (), "missing .cargo/config.toml")
LINKED_CHECK = FolderCheck(
    "rust linked projects",
    ("projects/bank-project-rust",),
    "missing from rust-analyzer.linkedProjects",
    "cstudy ide",
)


def with_folder_checks(runner: FolderCheckingRunner) -> PracticeWorkspace:
    return workspace_with(runners={**healthy_runners(), Language.RUST: runner})


def test_a_language_check_of_its_project_folders_passes_without_failing_folders():
    report = doctor(workspace=with_folder_checks(FolderCheckingRunner((CONFIG_CHECK,))))
    assert summary(report, "rust project config") == (OK, "")


def test_failing_project_folders_only_warn_listing_them_with_the_checks_fix():
    report = doctor(workspace=with_folder_checks(FolderCheckingRunner((LINKED_CHECK,))))
    result = check(report, "rust linked projects")
    assert (result.status, result.detail, result.fix, report.passed) == (
        WARN,
        "1 missing from rust-analyzer.linkedProjects: projects/bank-project-rust",
        "cstudy ide",
        True,
    )


def test_project_folders_are_not_checked_without_a_runner_that_checks_them():
    names = [result.name for result in doctor().results]
    assert ("go projects" in names, "rust project config" in names) == (False, False)


def test_a_folder_check_of_sentences_lists_them_apart_from_their_commas():
    problems = (
        "projects/a-project-go has no go.work",
        "projects/a-project-go, projects/b-project-go and projects/c-project-go all declare "
        "module bank",
    )
    go = FolderCheck("go projects", problems, "problems", separator="; ")
    result = check(doctor(workspace=with_folder_checks(FolderCheckingRunner((go,)))), "go projects")
    assert result.detail == (
        "2 problems: projects/a-project-go has no go.work; projects/a-project-go, "
        "projects/b-project-go and projects/c-project-go all declare module bank"
    )


def test_a_folder_check_shows_its_first_five_failures_and_counts_the_rest():
    folders = tuple(f"projects/p{number}" for number in range(1, 8))
    failing = replace(CONFIG_CHECK, failing=folders)
    report = doctor(workspace=with_folder_checks(FolderCheckingRunner((failing,))))
    assert check(report, "rust project config").detail == (
        "7 missing .cargo/config.toml: projects/p1, projects/p2, projects/p3, projects/p4, "
        "projects/p5 and 2 more"
    )


def test_a_folder_check_without_a_fix_of_its_own_is_fixed_by_doctor_fix():
    failing = replace(CONFIG_CHECK, failing=("projects/bank-project-rust",))
    report = doctor(workspace=with_folder_checks(FolderCheckingRunner((failing,))))
    assert check(report, "rust project config").fix == "cstudy doctor --fix"


def test_repair_writes_what_the_languages_folders_lack_and_names_it():
    runner = FolderCheckingRunner((), restored=("projects/bank-project-rust/.cargo/config.toml",))
    lines: list[str] = []
    repair_workspace(with_folder_checks(runner), lines.append)
    assert "wrote projects/bank-project-rust/.cargo/config.toml" in lines


INSTALLED_ASSETS = WebUiAssets(812_345)
INSTALLED_LIBRARIES = WebServerLibraries(("starlette 1.10.0", "uvicorn 0.54.0", "wsproto 1.3.2"))


@dataclass
class FakeWebUi:
    assets_found: WebUiAssets = INSTALLED_ASSETS
    libraries: WebServerLibraries = INSTALLED_LIBRARIES

    def assets(self) -> WebUiAssets:
        return self.assets_found

    def server_libraries(self) -> WebServerLibraries:
        return self.libraries


def web_rows(report: DoctorReport) -> list[tuple[str, CheckStatus, str, str | None]]:
    names = ("web ui assets", "web server")
    return [(r.name, r.status, r.detail, r.fix) for r in report.results if r.name in names]


def test_an_installed_web_ui_reports_its_size_and_server_versions():
    assert web_rows(doctor(web=FakeWebUi())) == [
        ("web ui assets", OK, "0.8 MB, digest matches", None),
        ("web server", OK, "starlette 1.10.0, uvicorn 0.54.0, wsproto 1.3.2", None),
    ]


def test_web_ui_assets_that_do_not_match_their_manifest_only_warn():
    web = FakeWebUi(assets_found=WebUiAssets(0, "missing editor.js"))
    report = doctor(web=web)
    assert (check(report, "web ui assets"), report.passed) == (
        CheckResult("web ui assets", WARN, "missing editor.js", "brew reinstall cstudy"),
        True,
    )


def test_web_server_libraries_that_do_not_import_only_warn():
    web = FakeWebUi(libraries=WebServerLibraries((), "uvicorn does not import: no uvicorn"))
    report = doctor(web=web)
    assert (check(report, "web server"), report.passed) == (
        CheckResult(
            "web server", WARN, "uvicorn does not import: no uvicorn", "brew reinstall cstudy"
        ),
        True,
    )


def test_the_web_ui_is_checked_in_a_workspace_only():
    report = doctor(workspace=NotFound("no workspace here"), web=FakeWebUi())
    assert web_rows(report) == []


def installs_row(report: DoctorReport) -> CheckResult:
    return check(report, "installs")


def test_a_single_install_passes_and_names_its_kind_version_and_path():
    assert installs_row(doctor()) == CheckResult(
        "installs", OK, "Homebrew 0.1.0 (/opt/homebrew/bin/cstudy)"
    )


def test_several_installs_only_warn_and_tell_which_to_remove():
    installs = FakeInstalls((UV_INSTALL, HOMEBREW_INSTALL), UV_INSTALL)
    report = doctor(installs=installs)
    row = installs_row(report)
    assert (row.status, report.passed) == (WARN, True)
    assert row.detail == (
        "2 cstudy installs on PATH: uv tool 0.0.9 (~/.local/bin/cstudy) runs first; "
        "Homebrew 0.1.0 (/opt/homebrew/bin/cstudy) is shadowed"
    )
    assert row.fix == (
        "keep Homebrew 0.1.0, the newest (uv tool 0.0.9 runs first and is older); "
        "uninstall the others: uv tool uninstall coding-study"
    )


def test_the_installs_row_follows_the_content_row_and_precedes_the_workspace():
    names = [result.name for result in doctor().results]
    assert names[names.index("content") + 1 : names.index("workspace")] == ["installs"]


def test_the_installs_row_is_there_outside_a_workspace_too():
    report = doctor(workspace=NotFound("no workspace here"))
    assert installs_row(report).status is OK


def test_the_reinstall_hint_names_the_install_that_is_running():
    web = FakeWebUi(libraries=WebServerLibraries((), "starlette does not import: no starlette"))
    report = doctor(web=web, installs=FakeInstalls((HOMEBREW_INSTALL,), HOMEBREW_INSTALL))
    assert check(report, "web server").fix == "brew reinstall cstudy"


def test_the_web_ui_assets_hint_names_the_running_install_too():
    web = FakeWebUi(assets_found=WebUiAssets(0, "missing editor.js"))
    report = doctor(web=web, installs=FakeInstalls((UV_INSTALL,), UV_INSTALL))
    assert check(report, "web ui assets").fix == "uv tool install --reinstall coding-study"


def test_the_reinstall_hint_does_not_send_the_user_to_a_shadowed_copy():
    web = FakeWebUi(libraries=WebServerLibraries((), "starlette does not import: no starlette"))
    installs = FakeInstalls((UV_INSTALL, HOMEBREW_INSTALL), UV_INSTALL)
    fix = check(doctor(web=web, installs=installs), "web server").fix
    assert fix == (
        "uv tool install --reinstall coding-study (several cstudy installs: see the installs row)"
    )


def test_the_docker_row_shows_the_versions_of_a_running_engine():
    assert summary(doctor(sandbox=FakeSandbox()), "docker") == (
        CheckStatus.OK,
        "engine 29.9.2, compose 5.6.1",
    )


def test_the_docker_row_warns_of_a_stopped_engine_and_names_the_fix():
    result = check(doctor(sandbox=FakeSandbox(engine=EngineState(EngineStatus.STOPPED))), "docker")

    assert (result.status, result.detail, result.fix) == (
        CheckStatus.WARN,
        "installed, not running",
        "cstudy doctor --fix",
    )


def test_a_missing_engine_is_a_warning_with_the_install_message_not_a_failure():
    report = doctor(sandbox=FakeSandbox(engine=EngineState(EngineStatus.NOT_INSTALLED)))
    result = check(report, "docker")

    assert result.status is CheckStatus.WARN
    assert "docs.docker.com" in (result.fix or "")
    assert report.passed


def test_no_permission_has_its_own_message():
    report = doctor(sandbox=FakeSandbox(engine=EngineState(EngineStatus.NO_PERMISSION)))

    assert "docker group" in (check(report, "docker").fix or "")


def test_plain_doctor_never_starts_the_engine():
    engine = FakeSandbox(engine=EngineState(EngineStatus.STOPPED))

    doctor(sandbox=engine)

    assert not engine.called("start_engine")


def test_the_leftovers_row_has_nothing_to_say_without_leftovers():
    assert summary(doctor(sandbox=FakeSandbox()), "docker leftovers") == (CheckStatus.OK, "none")


def test_the_leftovers_row_counts_and_names_the_fix():
    engine = FakeSandbox(
        inventory_found=SandboxInventory(
            containers=(StackContainer("cstudy-t-1-a", "test", "w", 1),),
            networks=(StackResource("cstudy-t-2-a_sandbox", "cstudy-t-2-a", "test", "w"),),
        )
    )

    result = check(doctor(sandbox=engine), "docker leftovers")

    assert result.status is CheckStatus.WARN
    assert result.detail.startswith("2 left")
    assert result.fix == "cstudy doctor --fix"


def test_the_leftovers_row_asks_nothing_of_a_stopped_engine():
    engine = FakeSandbox(engine=EngineState(EngineStatus.STOPPED))

    result = check(doctor(sandbox=engine), "docker leftovers")

    assert result.status is CheckStatus.OK
    assert not engine.called("inventory")


def test_doctor_fix_starts_a_stopped_engine():
    engine = FakeSandbox(engine=EngineState(EngineStatus.STOPPED))

    fix_sandbox(engine, lambda _line: None)

    assert engine.called("start_engine")


def test_doctor_fix_removes_leftovers_of_every_workspace():
    engine = FakeSandbox(
        inventory_found=SandboxInventory(
            containers=(StackContainer("cstudy-t-1-a", "test", "any", 1),)
        )
    )

    fix_sandbox(engine, lambda _line: None)

    assert [stack.name for stack in engine.called("remove_stack")] == ["cstudy-t-1-a"]  # type: ignore[attr-defined]


def test_doctor_fix_leaves_a_machine_without_docker_alone():
    engine = FakeSandbox(engine=EngineState(EngineStatus.NOT_INSTALLED))
    lines: list[str] = []

    fix_sandbox(engine, lines.append)

    assert lines == []
    assert not engine.called("start_engine")


def test_doctor_fix_says_when_the_engine_will_not_start_and_goes_on():
    stopped = EngineState(EngineStatus.STOPPED)
    engine = FakeSandbox(engine=stopped, started_engine_state=stopped)
    lines: list[str] = []

    fix_sandbox(engine, lines.append)

    assert any("did not start" in line for line in lines)
