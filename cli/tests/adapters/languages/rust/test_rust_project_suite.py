"""A Rust project's suite, one process per test (docs/specs/runners.md#rust-projects), with the
test binaries' processes scripted."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from coding_study.adapters.languages.rust.libtest import FinishedTest
from coding_study.adapters.languages.rust.project_build import BuiltTests, SuiteTarget
from coding_study.adapters.languages.rust.project_suite import (
    ONE_DEBUGGED_TEST,
    DebuggedTest,
    DebugTarget,
    LibtestSuite,
    SubprocessTests,
)
from coding_study.domain.debugging import DEBUGSERVER, LLDB_SERVER, DebugSession
from coding_study.domain.problem import Language
from coding_study.domain.runs import Crashed, Raised, TimedOut, UserError
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    SuiteFramework,
    SuiteJob,
    SuiteTest,
)

ROOT = Path("/ws/projects/bank")
LEVEL_1 = Path("/ws/.cs/build/rust-projects/bank/run/1-a/level_1-0123")
OWN = Path("/ws/.cs/build/rust-projects/bank/run/1-a/ledger-4567")
LIMIT_MS = 2_000
JOB = SuiteJob("bank/suite", SuiteFramework.LIBTEST, str(ROOT), LIMIT_MS)
OK = "\nrunning 1 test\ntest {name} ... ok\n\ntest result: ok. 1 passed; 0 failed; 0 ignored\n\n"
FAILED = (
    "\nrunning 1 test\n\nthread '{name}' panicked at tests/level_1.rs:9:5:\nwrong\n"
    "note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace\n"
    "test {name} ... FAILED\n\nfailures:\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored\n"
)
COMPILE_ERROR = UserError("CompileError", "tests/broken.rs:3:28: error[E0308]: mismatched types")


def listing(*names: str) -> FinishedTest:
    return FinishedTest(0, "".join(f"{name}: test\n" for name in names), 1)


def passing(name: str) -> FinishedTest:
    return FinishedTest(0, OK.format(name=name), 7)


@dataclass
class ScriptedTests:
    """Answers each command by the binary and the test it names."""

    answers: dict[tuple[str, str], FinishedTest | None]
    runs: list[tuple[tuple[str, ...], Path, int]] = field(
        default_factory=list[tuple[tuple[str, ...], Path, int]]
    )
    debugged: list[DebuggedTest] = field(default_factory=list[DebuggedTest])
    debug_output: str = ""

    def run(self, command: Sequence[str], cwd: Path, limit_ms: int) -> FinishedTest | None:
        self.runs.append((tuple(command), cwd, limit_ms))
        binary, *arguments = command
        key = "--list" if arguments[0] == "--list" else arguments[1]
        return self.answers[(Path(binary).name, key)]

    def debug(self, test: DebuggedTest) -> None:
        self.debugged.append(test)
        stdout = next(part for part in test.command if part.startswith("--stdout-path="))
        Path(stdout.removeprefix("--stdout-path=")).write_text(self.debug_output)
        test.announce()


@dataclass
class HeardTests:
    heard: list[str] = field(default_factory=list[str])

    def test_started(self, test_id: str) -> None:
        self.heard.append(f"start {test_id}")

    def test_finished(self, test: SuiteTest) -> None:
        self.heard.append(f"end {test.test_id}")


def built(*targets: SuiteTarget, scratch: Path | None = None) -> BuiltTests:
    return BuiltTests(targets, scratch)


LEVEL_TARGET = SuiteTarget("tests/level_1.rs", LEVEL_1)
OWN_TARGET = SuiteTarget("tests/ledger.rs", OWN)
BROKEN_TARGET = SuiteTarget("tests/broken.rs", error=COMPILE_ERROR)


def scripted(**extra: FinishedTest | None) -> ScriptedTests:
    answers: dict[tuple[str, str], FinishedTest | None] = {
        (LEVEL_1.name, "--list"): listing("ex1", "ex2"),
        (LEVEL_1.name, "ex1"): passing("ex1"),
        (LEVEL_1.name, "ex2"): FinishedTest(101, FAILED.format(name="ex2"), 9),
        (OWN.name, "--list"): listing("posts"),
        (OWN.name, "posts"): passing("posts"),
    }
    answers |= {(LEVEL_1.name, name): answer for name, answer in extra.items()}
    return ScriptedTests(answers)


def run(processes: ScriptedTests, tests: BuiltTests, job: SuiteJob = JOB, listener=None):
    return LibtestSuite(processes, job, listener).run(tests)


def test_each_test_of_each_target_is_reported_by_its_id_in_order():
    tests = run(scripted(), built(LEVEL_TARGET, OWN_TARGET))
    assert [test.test_id for test in tests] == [
        "tests/level_1.rs::ex1",
        "tests/level_1.rs::ex2",
        "tests/ledger.rs::posts",
    ]


def test_each_test_runs_alone_in_the_project_root_under_the_hang_guard():
    processes = scripted()
    run(processes, built(LEVEL_TARGET))
    assert processes.runs[1] == ((str(LEVEL_1), "--exact", "ex1", "--nocapture"), ROOT, LIMIT_MS)


def test_tests_are_listed_tersely():
    processes = scripted()
    run(processes, built(LEVEL_TARGET))
    assert processes.runs[0][0] == (str(LEVEL_1), "--list", "--format", "terse")


def test_each_test_is_judged_by_its_own_process():
    tests = run(scripted(), built(LEVEL_TARGET))
    assert tests == (
        SuiteTest("tests/level_1.rs::ex1", Passed(7)),
        SuiteTest("tests/level_1.rs::ex2", AssertionFailed("wrong\nat tests/level_1.rs:9:5", 9)),
    )


def test_a_hang_ends_only_its_own_test():
    tests = run(scripted(ex1=None), built(LEVEL_TARGET, OWN_TARGET))
    assert tests[0].outcome == TimedOut(LIMIT_MS)
    assert [test.test_id for test in tests][1:] == [
        "tests/level_1.rs::ex2",
        "tests/ledger.rs::posts",
    ]


def test_a_crash_ends_only_its_own_test():
    tests = run(scripted(ex1=FinishedTest(134, "\nrunning 1 test\n", 3)), built(LEVEL_TARGET))
    assert [test.outcome for test in tests] == [
        Crashed(134, ()),
        AssertionFailed("wrong\nat tests/level_1.rs:9:5", 9),
    ]


def test_a_target_that_does_not_compile_is_one_error_named_by_its_path():
    tests = run(scripted(), built(BROKEN_TARGET, LEVEL_TARGET))
    assert tests[0] == SuiteTest("tests/broken.rs", Raised(COMPILE_ERROR, 0))


def test_a_target_whose_tests_cannot_be_listed_is_one_error():
    processes = scripted()
    processes.answers[(OWN.name, "--list")] = FinishedTest(1, "cannot list\n", 1)
    tests = run(processes, built(OWN_TARGET))
    assert tests == (
        SuiteTest(
            "tests/ledger.rs",
            Raised(
                UserError("libtest", "cannot list the tests of tests/ledger.rs: cannot list"), 0
            ),
        ),
    )


@pytest.mark.parametrize("selection", ["tests/level_1.rs::ex2", "ex2"])
def test_a_selection_runs_only_the_tests_it_names(selection):
    job = SuiteJob(JOB.job_id, JOB.framework, JOB.root, LIMIT_MS, select=(selection,))
    tests = run(scripted(), built(LEVEL_TARGET, OWN_TARGET), job)
    assert [test.test_id for test in tests] == ["tests/level_1.rs::ex2"]


def test_a_listener_hears_each_test_start_and_end():
    listener = HeardTests()
    run(scripted(), built(BROKEN_TARGET, OWN_TARGET), listener=listener)
    assert listener.heard == [
        "start tests/broken.rs",
        "end tests/broken.rs",
        "start tests/ledger.rs::posts",
        "end tests/ledger.rs::posts",
    ]


def test_a_suite_without_targets_reports_no_tests():
    assert run(scripted(), built()) == ()


# debugging

SESSION = DebugSession(Language.RUST, 12345)


def debug(
    processes: ScriptedTests, tests: BuiltTests, server: str = DEBUGSERVER, job: SuiteJob = JOB
) -> tuple[tuple[SuiteTest, ...], str | None, list[str]]:
    announced: list[str] = []
    target = DebugTarget(SESSION, server, Path("/usr/bin/debugserver"), announced.append)
    tests_, stopped = LibtestSuite(processes, job, None).debug(tests, target)
    return tests_, stopped, announced


def test_a_debug_run_debugs_the_first_test_under_the_debug_server(tmp_path):
    processes = scripted()
    processes.debug_output = OK.format(name="ex1")
    debug(processes, built(LEVEL_TARGET, OWN_TARGET, scratch=tmp_path))
    (debugged,) = processes.debugged
    assert debugged.command == (
        "/usr/bin/debugserver",
        f"--stdout-path={tmp_path / 'stdout.txt'}",
        f"--stderr-path={tmp_path / 'stderr.txt'}",
        "--named-pipe",
        str(tmp_path / "debug-port"),
        "127.0.0.1:12345",
        "--",
        str(LEVEL_1),
        "--exact",
        "ex1",
        "--nocapture",
    )


def test_a_debug_run_reads_the_outcome_from_the_tests_output(tmp_path):
    processes = scripted()
    processes.debug_output = FAILED.format(name="ex1")
    tests, _, _ = debug(processes, built(LEVEL_TARGET, scratch=tmp_path))
    assert tests == (
        SuiteTest("tests/level_1.rs::ex1", AssertionFailed("wrong\nat tests/level_1.rs:9:5", 0)),
    )


def test_a_debug_run_says_that_the_other_tests_did_not_run(tmp_path):
    processes = scripted()
    processes.debug_output = OK.format(name="ex1")
    _, stopped, _ = debug(processes, built(LEVEL_TARGET, OWN_TARGET, scratch=tmp_path))
    assert stopped == ONE_DEBUGGED_TEST


def test_a_debug_run_of_the_only_selected_test_stopped_nothing(tmp_path):
    processes = scripted()
    processes.debug_output = OK.format(name="ex2")
    job = SuiteJob(JOB.job_id, JOB.framework, JOB.root, LIMIT_MS, select=("ex2",))
    tests, stopped, _ = debug(processes, built(LEVEL_TARGET, OWN_TARGET, scratch=tmp_path), job=job)
    assert ([test.test_id for test in tests], stopped) == (["tests/level_1.rs::ex2"], None)


def test_a_debug_run_announces_the_ready_line(tmp_path):
    processes = scripted()
    processes.debug_output = OK.format(name="ex1")
    _, _, announced = debug(processes, built(LEVEL_TARGET, scratch=tmp_path))
    assert announced == [SESSION.ready_line]


def test_a_debugged_test_that_never_reported_crashed(tmp_path):
    processes = scripted()
    processes.debug_output = "\nrunning 1 test\nlast words\n"
    tests, _, _ = debug(processes, built(LEVEL_TARGET, scratch=tmp_path))
    assert tests[0].outcome == Crashed(-1, ("last words",))


class LldbServerTests(ScriptedTests):
    def debug(self, test: DebuggedTest) -> None:
        self.debugged.append(test)


def test_under_lldb_server_the_outcome_is_not_known(tmp_path):
    processes = LldbServerTests(scripted().answers)
    tests, _, _ = debug(processes, built(LEVEL_TARGET, scratch=tmp_path), server=LLDB_SERVER)
    assert tests[0].outcome == Raised(
        UserError("libtest", "the outcome of a test debugged under lldb-server is not known"), 0
    )


def test_lldb_server_runs_as_a_gdbserver_without_output_files(tmp_path):
    processes = LldbServerTests(scripted().answers)
    debug(processes, built(LEVEL_TARGET, scratch=tmp_path), server=LLDB_SERVER)
    assert processes.debugged[0].command[:3] == (
        "/usr/bin/debugserver",
        "gdbserver",
        "--named-pipe",
    )


# real processes


@pytest.fixture
def script(tmp_path: Path) -> Callable[[str], Path]:
    def write(body: str) -> Path:
        path = tmp_path / "test-binary"
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(0o755)
        return path

    return write


def test_a_process_reports_its_exit_code_and_its_output_together(script, tmp_path):
    binary = script("echo out; echo err >&2; exit 101")
    finished = SubprocessTests().run((str(binary),), tmp_path, LIMIT_MS)
    assert finished is not None
    assert (finished.exit_code, finished.output) == (101, "out\nerr\n")


def test_a_process_ended_by_a_signal_exits_with_128_plus_the_signal(script, tmp_path):
    binary = script("kill -ABRT $$")
    finished = SubprocessTests().run((str(binary),), tmp_path, LIMIT_MS)
    assert finished is not None
    assert finished.exit_code == 134


def test_a_process_past_its_limit_is_killed_with_its_group(script, tmp_path):
    binary = script(f"sleep 30 & echo $! > {tmp_path}/child; wait")
    assert SubprocessTests().run((str(binary),), tmp_path, 300) is None


def test_a_test_runs_without_the_users_backtrace_settings(script, tmp_path, monkeypatch):
    monkeypatch.setenv("RUST_BACKTRACE", "1")
    monkeypatch.setenv("RUST_TEST_THREADS", "4")
    binary = script('echo "${RUST_BACKTRACE:-unset} ${RUST_TEST_THREADS:-unset}"')
    finished = SubprocessTests().run((str(binary),), tmp_path, LIMIT_MS)
    assert finished is not None
    assert finished.output == "unset unset\n"
