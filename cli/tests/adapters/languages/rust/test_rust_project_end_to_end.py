"""A Rust project folder graded and suite-run through real cargo, offline, and the real Rust runner
(docs/specs/runners.md#rust-projects).

The fixture crate `bank` re-exports `Bank` at its root and keeps the balances in its module
`src/ledger.rs`, so every grading reaches the crate through the harness's path dependency, and
every suite runs each test of each target as a process of its own. The level test files are the
real generator's.
"""

import shutil
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.debug_servers import InstalledDebugServers, this_machine
from coding_study.adapters.languages.rust import create_runner
from coding_study.adapters.languages.rust.test_generator import RustTestGenerator
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.application.project_runs import GradingRun, SuiteRun, run_grading, run_suite
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.config import Config, HangGuardSettings
from coding_study.domain.debugging import DebugSession
from coding_study.domain.judging import Judgement
from coding_study.domain.levels import cases_up_to
from coding_study.domain.problem import Language, Problem
from coding_study.domain.project import level_test_file
from coding_study.domain.project_tests import level_tests
from coding_study.domain.runs import Crashed, Raised, TimedOut
from coding_study.domain.suite_runs import AssertionFailed, Passed, Skipped, SuiteReport, SuiteTest
from tests.debug_clients import free_port, run_lldb_client
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import RUST_BANK_PROJECT, RUST_PROJECT_PROBLEMS
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("cargo") is None, reason="cargo is not installed"),
]

SLUG = "bank-project-rust"
FIXTURE = RUST_PROJECT_PROBLEMS / RUST_BANK_PROJECT
LAST_LEVEL = 2
CASES_THROUGH_LAST_LEVEL = 6
HANG_GUARD_MS = 1000
READY_TIMEOUT_SECONDS = 120.0
POLL_SECONDS = 0.05
LEDGER_OPEN_LINE = 13
"""The first statement of `Ledger::open` in the reference's src/ledger.rs."""
ABORTED_EXIT = 128 + signal.SIGABRT
NO_LLDB = InstalledDebugServers(this_machine()).lldb_server().path is None or not shutil.which(
    "lldb"
)
STATUSES = """\
use std::process;
use std::thread;
use std::time::Duration;

use bank::Bank;

#[test]
fn passes() {
    assert!(Bank::new().create_account(1, "ivy".to_string()));
}

#[test]
fn panics() {
    panic!("a failure");
}

#[test]
fn hangs() {
    loop {
        thread::sleep(Duration::from_secs(1));
    }
}

#[test]
fn aborts() {
    process::abort();
}

#[test]
fn prints() {
    println!("some output");
}

#[test]
#[ignore = "not today"]
fn is_ignored() {}

#[test]
#[should_panic(expected = "a failure")]
fn panics_as_expected() {
    panic!("a failure");
}
"""
PANIC_LINE = 14
"""`panic!("a failure");` in `panics`, at column 5."""
BROKEN = """\
#[test]
fn does_not_compile() {
    let count: i32 = "three";
    assert_eq!(count, 3);
}
"""
NOT_COMPILING_ENTRY = """\
pub struct Bank {}

impl Bank {
    pub fn new() -> Self {
        Bank {}
    }

    pub fn create_account(&mut self, timestamp: i64, account_id: String) -> bool {
        account_id.len()
    }

    pub fn deposit(&mut self, timestamp: i64, account_id: String, amount: i64) -> i64 {
        amount
    }
}
"""


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("workspace"))
    return repository_root(root, RUST_PROJECT_PROBLEMS)


@pytest.fixture(scope="module")
def environment(workspace: Path) -> Environment:
    runner = create_runner(LanguageContext(workspace, workspace / RUNTIME_RUNNERS))
    return make_environment(
        workspace,
        config=Config(hang_guard=HangGuardSettings(ms=HANG_GUARD_MS)),
        toolchains=FakeToolchains(runners={Language.RUST: runner}),
        runner_process=SubprocessRunner(workspace / ".cs" / "runs"),
    )


@pytest.fixture(scope="module")
def problem(environment: Environment) -> Problem:
    return environment.problems.load(SLUG)


def project_folder(workspace: Path, problem: Problem, name: str, *overlays: str) -> Path:
    """`projects/<name>/`: the starter, each overlay of `solutions/` on it, and the generated
    test file of every level."""
    folder = workspace / "projects" / name
    shutil.copytree(FIXTURE / "starter", folder)
    for overlay in overlays:
        shutil.copytree(FIXTURE / "solutions" / overlay, folder, dirs_exist_ok=True)
    project = problem.meta.project
    assert project is not None
    for level in range(1, LAST_LEVEL + 1):
        path = folder / level_test_file(project, Language.RUST, level)
        path.parent.mkdir(exist_ok=True)
        path.write_text(RustTestGenerator().generate(level_tests(problem, level)))
    return folder


def with_file(folder: Path, path: str, text: str) -> Path:
    (folder / path).write_text(text, encoding="utf-8")
    return folder


def grade(environment: Environment, problem: Problem, folder: Path, level: int) -> Judgement:
    run = GradingRun(problem, Language.RUST, folder, level)
    return run_grading(environment, run, print)


@dataclass
class HeardTests:
    started: list[str] = field(default_factory=list[str])
    finished: list[str] = field(default_factory=list[str])

    def test_started(self, test_id: str) -> None:
        self.started.append(test_id)

    def test_finished(self, test: SuiteTest) -> None:
        self.finished.append(test.test_id)


def suite(
    environment: Environment, problem: Problem, folder: Path, listener: HeardTests | None = None
) -> SuiteReport:
    run = SuiteRun(problem.meta, Language.RUST, folder, LAST_LEVEL, listener=listener)
    return run_suite(environment, run, print)


def test_the_reference_over_its_starter_passes_every_case_of_every_level(
    workspace, environment, problem
):
    folder = project_folder(workspace, problem, "reference", "reference")
    judgement = grade(environment, problem, folder, LAST_LEVEL)
    assert (judgement.passed, judgement.case_count) == (True, CASES_THROUGH_LAST_LEVEL)


def test_the_bare_starter_builds_and_fails_the_level_1_cases_with_errors(
    workspace, environment, problem
):
    folder = project_folder(workspace, problem, "starter")
    judgement = grade(environment, problem, folder, 1)
    level_1_cases = len(cases_up_to(problem.cases, 1))
    assert (judgement.load_error, judgement.count(CaseStatus.ERROR)) == (None, level_1_cases)


def test_grading_a_level_whose_method_is_missing_names_the_method(workspace, environment, problem):
    folder = project_folder(workspace, problem, "starter-at-level-2")
    load_error = grade(environment, problem, folder, LAST_LEVEL).load_error
    assert load_error is not None
    assert "transfer" in load_error.message


def test_a_project_that_does_not_compile_fails_its_grading_with_the_compiler_error(
    workspace, environment, problem
):
    folder = project_folder(workspace, problem, "not-compiling")
    with_file(folder, "src/lib.rs", NOT_COMPILING_ENTRY)
    load_error = grade(environment, problem, folder, 1).load_error
    assert load_error is not None
    assert (load_error.type, "src/lib.rs:9:9" in load_error.trace) == ("CompileError", True)


def test_the_suite_of_level_1_leaves_the_locked_levels_file_out(workspace, environment, problem):
    folder = project_folder(workspace, problem, "suite-level-1", "reference")
    run = SuiteRun(problem.meta, Language.RUST, folder, 1)
    report = run_suite(environment, run, print)
    assert [(test.test_id, type(test.outcome)) for test in report.tests] == [
        ("tests/level_1.rs::ex1", Passed),
    ]


@pytest.fixture(scope="module")
def heard() -> HeardTests:
    return HeardTests()


@pytest.fixture(scope="module")
def statuses(workspace, environment, problem, heard) -> dict[str, SuiteTest]:
    """One suite of the reference with a test of every status and a file that does not
    compile."""
    folder = project_folder(workspace, problem, "statuses", "reference")
    with_file(folder, "tests/statuses.rs", STATUSES)
    with_file(folder, "tests/broken.rs", BROKEN)
    report = suite(environment, problem, folder, heard)
    return {test.test_id: test for test in report.tests}


def outcome_of(statuses: dict[str, SuiteTest], name: str):
    return statuses[f"tests/statuses.rs::{name}"].outcome


def test_a_suite_reports_every_test_of_every_target_and_the_target_that_did_not_compile(
    statuses,
):
    assert {test_id: type(test.outcome).__name__ for test_id, test in statuses.items()} == {
        "tests/broken.rs": "Raised",
        "tests/level_1.rs::ex1": "Passed",
        "tests/level_2.rs::ex2": "Passed",
        "tests/statuses.rs::aborts": "Crashed",
        "tests/statuses.rs::hangs": "TimedOut",
        "tests/statuses.rs::is_ignored": "Skipped",
        "tests/statuses.rs::panics": "AssertionFailed",
        "tests/statuses.rs::panics_as_expected": "Passed",
        "tests/statuses.rs::passes": "Passed",
        "tests/statuses.rs::prints": "Passed",
    }


def test_a_test_file_that_does_not_compile_has_the_compilers_error(statuses):
    outcome = statuses["tests/broken.rs"].outcome
    assert isinstance(outcome, Raised)
    assert "mismatched types" in outcome.error.message


def test_a_panic_fails_its_test_with_the_message_and_the_location_in_the_folder(statuses):
    outcome = outcome_of(statuses, "panics")
    assert isinstance(outcome, AssertionFailed)
    assert outcome.message == f"a failure\nat tests/statuses.rs:{PANIC_LINE}:5"


def test_a_hang_ends_only_its_own_test_at_the_hang_guard(statuses):
    assert outcome_of(statuses, "hangs") == TimedOut(HANG_GUARD_MS)


def test_an_abort_crashes_only_its_own_test(statuses):
    outcome = outcome_of(statuses, "aborts")
    assert isinstance(outcome, Crashed)
    assert outcome.exit_code == ABORTED_EXIT


def test_a_passing_test_keeps_what_it_printed(statuses):
    outcome = outcome_of(statuses, "prints")
    assert isinstance(outcome, Passed)
    assert outcome.stdout == "some output\n"


def test_an_ignored_test_is_skipped_with_its_reason(statuses):
    outcome = outcome_of(statuses, "is_ignored")
    assert isinstance(outcome, Skipped)
    assert outcome.message == "not today"


def test_the_listener_hears_each_test_start_and_finish_in_the_reports_order(statuses, heard):
    reported = list(statuses)
    assert (heard.started, heard.finished) == (reported, reported)


@pytest.mark.skipif(NO_LLDB, reason="lldb or its debug server is not installed")
def test_a_debugged_test_stops_at_a_breakpoint_in_the_projects_code(
    workspace, environment, problem
):
    folder = project_folder(workspace, problem, "debugged", "reference")
    session = DebugSession(Language.RUST, free_port())
    notices: list[str] = []
    select = ("tests/level_1.rs::ex1",)
    run = SuiteRun(problem.meta, Language.RUST, folder, 1, select=select, debug=session)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(run_suite, environment, run, notices.append)
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while session.ready_line not in notices and time.monotonic() < deadline:
            time.sleep(POLL_SECONDS)
        printed = run_lldb_client(session.port, folder / "src" / "ledger.rs", LEDGER_OPEN_LINE)
        report = running.result(timeout=READY_TIMEOUT_SECONDS)
    assert "stop reason = breakpoint 1.1" in printed
    assert [(test.test_id, type(test.outcome)) for test in report.tests] == [
        ("tests/level_1.rs::ex1", Passed),
    ]
