from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.application.doctor import (
    HANDSHAKE_META,
    CheckResult,
    CheckStatus,
    ContentLocation,
    DoctorEnvironment,
    DoctorReport,
    NotFound,
    PracticeWorkspace,
    fix_workspace,
    repair_workspace,
    run_doctor,
)
from coding_study.application.ports import (
    BuildFailed,
    CaseListener,
    DebugServer,
    LanguageRunner,
    Prepared,
    ProbeResult,
    RunnerLaunch,
    ScaffoldOutcome,
    SuiteListener,
    UserCode,
)
from coding_study.domain.bench_runs import BenchReport, BenchRequest
from coding_study.domain.config import Config
from coding_study.domain.errors import ConfigError, RunnerProtocolError, RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import RunnerInfo, RunReport, RunRequest
from coding_study.domain.suite_runs import SuiteJob, SuiteReport
from coding_study.domain.workspace_projects import GoProjectFolder
from tests.fakes import DEBUGSERVER, DELVE, FakeDebugServers, FakeLanguageRunner, FakeToolchains

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
    ("java", "-version"): ProbeResult(
        0, 'openjdk version "21.0.2" 2024-01-16\nOpenJDK Runtime Environment (build 21.0.2+13)\n'
    ),
    ("gradle", "--version"): ProbeResult(0, "\n------\nGradle 9.8.2\n------\n"),
    ("go", "version"): ProbeResult(0, "go version go1.24.1 darwin/arm64\n"),
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
TOOLCHAINS_GUIDE = "https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md"


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

    def run(self, command: Sequence[str], cwd: Path) -> ProbeResult | None:
        self.ran.append((tuple(command), cwd))
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


def healthy_runners() -> dict[Language, LanguageRunner]:
    return {
        language: FakeLanguageRunner(Prepared(RunnerLaunch((language.value,), Path("/"), 1000)))
        for language in Language
    }


def workspace_with(
    paths: set[str] | None = None,
    runners: dict[Language, LanguageRunner] | None = None,
    process: HelloProcess | None = None,
    commands: FakeCommands | None = None,
    setup: FakeSetup | None = None,
    links: FakeProjectLinks | None = None,
) -> PracticeWorkspace:
    return PracticeWorkspace(
        files=FakeFiles(set(COMPLETE_WORKSPACE) if paths is None else paths),
        created_with=RUNNING_VERSION,
        setup=setup or FakeSetup(),
        toolchains=FakeToolchains(healthy_runners() if runners is None else runners),
        runner_process=process or HelloProcess(),
        commands=commands or FakeCommands(),
        project_links=links or FakeProjectLinks(),
    )


def doctor(
    tools: FakeTools | None = None,
    config: FakeConfigSource | None = None,
    workspace: PracticeWorkspace | NotFound | None = None,
    content: ContentLocation | NotFound = BUNDLED,
    debug_servers: FakeDebugServers | None = None,
) -> DoctorReport:
    return run_doctor(
        DoctorEnvironment(
            tools=tools or FakeTools(),
            debug_servers=debug_servers or FakeDebugServers(),
            config=config or FakeConfigSource(),
            content=content,
            workspace=workspace or workspace_with(),
            version=RUNNING_VERSION,
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
        ("java", OK, "21.0.2"),
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
    ("output", "expected"),
    [
        ('openjdk version "21" 2023-09-19', (OK, "21")),
        ('openjdk version "17.0.9" 2023-10-17', (FAIL, "17.0.9 (need JDK 21)")),
        ('openjdk version "25.0.1" 2025-10-21', (FAIL, "25.0.1 (need JDK 21)")),
        ('java version "1.8.0_391"', (FAIL, "1.8.0 (need JDK 21)")),
    ],
)
def test_java_must_be_21(output, expected):
    tools = tools_with(("java", "-version"), ProbeResult(0, output))
    assert summary(doctor(tools), "java") == expected


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
        (("java", "-version"), "java", f"install JDK 21: {TOOLCHAINS_GUIDE}#jdk-21"),
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
        ("go", OK, "1.24.1"),
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
        ("go version go1.24 linux/amd64", OK),
        ("go version go1.25rc1 linux/amd64", OK),
        ("go version devel go1.26-abc123 Mon Jan 1 00:00:00 2026 darwin/arm64", OK),
        ("go version go1.23.9 darwin/arm64", WARN),
        ("go version go1.9.7 linux/amd64", WARN),
    ],
)
def test_go_must_be_1_24_or_newer(output, expected):
    tools = tools_with(("go", "version"), ProbeResult(0, output))
    assert check(doctor(tools), "go").status is expected


def test_old_go_says_cstudy_never_downloads_a_toolchain():
    tools = tools_with(("go", "version"), ProbeResult(0, "go version go1.23.9 darwin/arm64"))
    assert summary(doctor(tools), "go") == (
        WARN,
        "1.23.9 (need 1.24 or newer; cstudy builds with GOTOOLCHAIN=local and never downloads one)",
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
        "uv add --dev pytest --directory python",
        True,
    )


def test_pytest_is_not_checked_before_the_venv_exists():
    report = doctor(workspace=workspace_with(COMPLETE_WORKSPACE - {"python/.venv"}))
    assert "python pytest" not in [result.name for result in report.results]


def test_project_rows_follow_the_workspace_files_in_the_specs_order():
    names = [result.name for result in doctor().results]
    rows = ["projects", "python pytest", "project links", "python/.venv location"]
    assert [name for name in names if name in rows] == rows


class GoFoldersRunner(FakeLanguageRunner):
    """A Go runner that finds `folders` and writes the missing `go.work` files."""

    def __init__(self, *folders: GoProjectFolder) -> None:
        super().__init__(Prepared(RunnerLaunch(("go",), Path("/"), 1000)))
        self.folders = folders
        self.repaired = 0

    def go_project_folders(self) -> tuple[GoProjectFolder, ...]:
        return self.folders

    def write_missing_go_work_files(self) -> tuple[str, ...]:
        self.repaired += 1
        return tuple(found.folder for found in self.folders if not found.has_work_file)


def with_go_folders(*folders: GoProjectFolder) -> PracticeWorkspace:
    return workspace_with(runners={**healthy_runners(), Language.GO: GoFoldersRunner(*folders)})


def go_folder(slug: str, **changes: object) -> GoProjectFolder:
    return replace(GoProjectFolder(f"projects/{slug}", slug, has_work_file=True), **changes)


def test_go_project_folders_with_their_go_work_and_own_modules_pass():
    report = doctor(workspace=with_go_folders(go_folder("a-project-go")))
    assert summary(report, "go projects") == (OK, "")


def test_a_go_folder_without_its_go_work_only_warns_with_the_fix_command():
    folder = go_folder("a-project-go", has_work_file=False)
    report = doctor(workspace=with_go_folders(folder))
    result = check(report, "go projects")
    assert (result.status, result.detail, result.fix, report.passed) == (
        WARN,
        "1 problem: projects/a-project-go has no go.work",
        "cstudy doctor --fix",
        True,
    )


def test_a_go_replacement_that_does_not_resolve_points_to_the_restore():
    folder = go_folder("a-project-go", unresolved=("../../gone",))
    result = check(doctor(workspace=with_go_folders(folder)), "go projects")
    assert result.fix == "cstudy start a-project-go --restore go.mod"


def test_two_go_folders_with_one_module_say_so():
    folders = (go_folder("a-project-go", module="bank"), go_folder("b-project-go", module="bank"))
    result = check(doctor(workspace=with_go_folders(*folders)), "go projects")
    assert (result.detail, result.fix) == (
        "1 problem: projects/a-project-go and projects/b-project-go both declare module bank",
        "give each folder a module of its own in its go.mod",
    )


def test_go_folders_are_not_checked_without_a_go_runner_that_finds_them():
    assert "go projects" not in [result.name for result in doctor().results]


def test_repair_writes_the_missing_go_work_files():
    lines: list[str] = []
    workspace = with_go_folders(go_folder("a-project-go", has_work_file=False))
    repair_workspace(workspace, lines.append)
    assert "wrote projects/a-project-go/go.work" in lines


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
):
    return fix_workspace(workspace, content, notify)


def test_fix_runs_the_setup_command_of_every_workspace_project():
    commands = FakeCommands()
    fix(workspace_with(commands=commands))
    assert commands.ran == [
        (("uv", "sync"), Path("/ws/python")),
        (("pnpm", "install"), Path("/ws/typescript")),
        (
            ("./gradlew", ":java:classes", ":kotlin:classes", "-Pcs.only=cs_doctor_handshake"),
            Path("/ws/jvm"),
        ),
    ]


def test_fix_installs_the_typescript_runner_of_a_content_checkout():
    commands = FakeCommands()
    fix(workspace_with(commands=commands), CHECKOUT)
    assert commands.ran[2] == (("pnpm", "install"), Path("/checkout/runners/typescript"))


def test_fix_skips_projects_that_are_not_set_up():
    commands = FakeCommands()
    fix(workspace_with(paths={"python"}, commands=commands))
    assert [command for command, _cwd in commands.ran] == [("uv", "sync")]


def test_fix_reports_each_command_outcome():
    commands = FakeCommands({("pnpm", "install"): ProbeResult(1, "ERR_PNPM_FETCH\n")})
    outcomes = fix(workspace_with(commands=commands), CHECKOUT)
    assert [(outcome.step.project, outcome.succeeded) for outcome in outcomes] == [
        ("python", True),
        ("typescript", False),
        ("runners/typescript", False),
        ("jvm", True),
    ]


def test_fix_with_a_missing_tool_fails_that_step():
    commands = FakeCommands({("uv", "sync"): None})
    outcomes = fix(workspace_with(commands=commands))
    assert outcomes[0].detail == "uv not found on PATH"


def test_fix_announces_each_command_before_running_it():
    lines: list[str] = []
    fix(workspace_with(paths={"jvm"}), notify=lines.append)
    assert lines == [
        "running ./gradlew :java:classes :kotlin:classes -Pcs.only=cs_doctor_handshake (in jvm)"
    ]


def test_any_failure_fails_the_report():
    assert doctor(tools_with(("node", "--version"), None)).passed is False
