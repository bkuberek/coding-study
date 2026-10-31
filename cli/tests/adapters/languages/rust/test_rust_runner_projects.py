"""The Rust runner's project jobs (docs/specs/runners.md#rust-projects): a grading launches the
harness built from the job, and a suite runs in the runner itself."""

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.rust.runner import COLD_NOTICE, RustRunner
from coding_study.application.ports import (
    BuildFailed,
    DebugServer,
    HostedSuite,
    ProjectGrading,
    ProjectSuite,
    ProjectSuiteHost,
    RunnerLaunch,
)
from coding_study.domain.debugging import DEBUGSERVER, DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import RunnerInfo, UserError
from coding_study.domain.suite_runs import SuiteFramework, SuiteJob
from tests.adapters.languages.rust.test_rust_project_build import (
    BUILT,
    MANIFEST,
    SLUG,
    SUITE,
    ReplayedCargo,
)
from tests.adapters.languages.rust.test_rust_project_suite import ScriptedTests, listing, passing
from tests.fakes import FakeDebugServers
from tests.project_builders import project_meta

META = project_meta(language=Language.RUST)


@pytest.fixture
def workspace(tmp_path):
    root = (tmp_path / "ws").resolve()
    folder = root / "projects" / SLUG
    folder.mkdir(parents=True)
    (folder / "Cargo.toml").write_text(MANIFEST)
    (root / ".cs/runtime/runners/rust").mkdir(parents=True)
    return root


def rust_runner(workspace, cargo, tests=None, debug_servers=None) -> RustRunner:
    context = LanguageContext(workspace, workspace / ".cs/runtime/runners")
    return RustRunner(context, cargo, debug_servers or FakeDebugServers(), tests)


def grading(workspace, *outputs, notices: list[str] | None = None):
    cargo = ReplayedCargo(workspace, list(outputs))
    scope = ProjectGrading(workspace / "projects" / SLUG, META, 2)
    heard = notices if notices is not None else []
    return rust_runner(workspace, cargo).prepare_project(scope, heard.append)


def test_the_rust_runner_hosts_its_suites():
    assert issubclass(RustRunner, ProjectSuiteHost)


def test_a_grading_launches_the_harness_in_the_project_root(workspace):
    launch = grading(workspace, BUILT)
    assert isinstance(launch, RunnerLaunch)
    assert launch.cwd == workspace / "projects" / SLUG
    assert launch.command[0].endswith("project_bank_project_rust")


def test_a_grading_launches_a_private_copy_removed_with_its_run(workspace):
    launch = grading(workspace, BUILT)
    assert isinstance(launch, RunnerLaunch)
    assert launch.scratch is not None
    assert launch.command[0].startswith(str(launch.scratch))


def test_the_first_grading_says_the_runner_compiles(workspace):
    notices: list[str] = []
    grading(workspace, BUILT, notices=notices)
    grading(workspace, BUILT, notices=notices)
    assert notices == [COLD_NOTICE]


def test_a_grading_of_a_project_that_does_not_compile_fails_its_build(workspace):
    assert isinstance(grading(workspace, (101, "project-harness-user-error", "")), BuildFailed)


def test_a_grading_without_its_job_cannot_build_a_bridge(workspace):
    runner = rust_runner(workspace, ReplayedCargo(workspace))
    with pytest.raises(ValueError, match="graded problem"):
        runner.prepare_project(ProjectGrading(workspace / "projects" / SLUG), [].append)


def test_a_suite_is_never_prepared_as_a_launch(workspace):
    runner = rust_runner(workspace, ReplayedCargo(workspace))
    with pytest.raises(ValueError, match="run_project_suite"):
        runner.prepare_project(ProjectSuite(workspace / "projects" / SLUG), [].append)


def suite_job(workspace) -> SuiteJob:
    return SuiteJob(
        f"{SLUG}/suite", SuiteFramework.LIBTEST, str(workspace / "projects" / SLUG), 2000
    )


def scripted_statuses() -> ScriptedTests:
    return ScriptedTests(
        {
            ("statuses-23d59589c8c63527", "--list"): listing("passes"),
            ("statuses-23d59589c8c63527", "passes"): passing("passes"),
            ("bank-f91d9cd818ee8a14", "--list"): listing(),
        }
    )


def test_a_suite_reports_each_test_and_each_target_that_did_not_compile(workspace):
    runner = rust_runner(workspace, ReplayedCargo(workspace, [SUITE]), scripted_statuses())
    report = runner.run_project_suite(HostedSuite(SLUG, suite_job(workspace)), [].append)
    assert [test.test_id for test in report.tests] == [
        "tests/broken.rs",
        "tests/statuses.rs::passes",
    ]


def test_a_suites_runner_is_rust_with_the_rustc_release(workspace):
    runner = rust_runner(workspace, ReplayedCargo(workspace, [SUITE]), scripted_statuses())
    report = runner.run_project_suite(HostedSuite(SLUG, suite_job(workspace)), [].append)
    assert report.runner == RunnerInfo("rust", 1, "1.92.0")


def test_a_suite_removes_the_copies_of_its_binaries(workspace):
    runner = rust_runner(workspace, ReplayedCargo(workspace, [SUITE]), scripted_statuses())
    runner.run_project_suite(HostedSuite(SLUG, suite_job(workspace)), [].append)
    runs = workspace / ".cs/build/rust-projects" / SLUG / "run"
    assert list(runs.iterdir()) == []


def test_a_suite_of_a_project_cargo_cannot_read_has_a_load_error(workspace):
    (workspace / "projects" / SLUG / "Cargo.toml").unlink()
    runner = rust_runner(workspace, ReplayedCargo(workspace))
    report = runner.run_project_suite(HostedSuite(SLUG, suite_job(workspace)), [].append)
    assert report.load_error == UserError("CargoError", "Cargo.toml is missing")


def test_a_debug_run_without_the_debug_server_fails_before_building(workspace):
    cargo = ReplayedCargo(workspace, [SUITE])
    servers = FakeDebugServers(lldb=DebugServer(DEBUGSERVER, "run `xcode-select --install`"))
    runner = rust_runner(workspace, cargo, scripted_statuses(), servers)
    suite = HostedSuite(SLUG, suite_job(workspace), DebugSession(Language.RUST, 12345))
    with pytest.raises(RunnerStartError, match="debugserver was not found"):
        runner.run_project_suite(suite, [].append)
    assert cargo.builds == []
