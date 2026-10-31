"""`cstudy test --debug` (docs/specs/cli.md#cstudy-test): options, the ready line and the report."""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.ports import (
    BuildScope,
    CaseListener,
    DebugLaunch,
    Prepared,
    PrepareResult,
    ProgressNotice,
    RunnerLaunch,
    UserCode,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.domain.runs import Returned, RunCase, RunJob, RunReport, RunRequest
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import (
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
    two_sum,
)

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
READY_LINE = "cstudy: waiting for debugger on 127.0.0.1:5678 (python)"
TIMING = re.compile(r"\d+(\.\d+)?(ms|s)\b")


class DebuggableRunner:
    """Prepares a launch with a debug agent, whose ready line goes through the notice."""

    def __init__(self) -> None:
        self.scopes: list[BuildScope] = []

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        self.scopes.append(scope)
        debug = None
        if isinstance(scope, UserCode) and scope.debug is not None:
            debug = DebugLaunch(scope.debug, notify)
        return Prepared(RunnerLaunch(("fake-runner",), Path("/"), 1000, debug))


class AnnouncingProcess(ScriptedRunnerProcess):
    """Says the session's ready line as a real runner does once its agent listens."""

    def __init__(self, interrupted: bool = False) -> None:
        super().__init__(two_sum)
        self.interrupted = interrupted

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        if launch.debug is not None:
            launch.debug.announce(launch.debug.session.ready_line)
        if self.interrupted:
            raise KeyboardInterrupt
        return super().run(launch, request, listener)


def wrong(job: RunJob, case: RunCase) -> Returned:
    return Returned([9, 9], 1000)


@pytest.fixture
def prepared_runner() -> DebuggableRunner:
    return DebuggableRunner()


def started_environment(tmp_path, monkeypatch, prepared_runner, process):
    toolchains = FakeToolchains(
        {Language.PYTHON: prepared_runner}, {Language.PYTHON: FakeStubGenerator()}
    )
    environment = make_environment(
        repository_root(tmp_path, PRACTICE), toolchains=toolchains, runner_process=process
    )
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


@pytest.fixture
def environment(tmp_path, monkeypatch, prepared_runner):
    return started_environment(tmp_path, monkeypatch, prepared_runner, AnnouncingProcess())


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["test", *arguments])


def debugged(*arguments: str):
    return invoke("--debug", *arguments)


def report_lines(result) -> list[str]:
    return result.stdout.splitlines()


@pytest.mark.parametrize(
    "flag",
    [
        ["--watch"],
        ["--perf"],
        ["--json"],
        ["--stress", "2"],
        ["--seed", "3"],
        ["--time-limit"],
        ["--time-limit=5x"],
    ],
)
def test_debug_refuses_what_cannot_be_paused(environment, flag):
    result = debugged(*flag)
    refusal = f"error: --debug excludes {flag[0].split('=')[0]}"
    assert (result.exit_code, refusal in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_debug_names_every_option_it_excludes(environment):
    result = debugged("--perf", "--watch", "--json")
    assert "error: --debug excludes --watch, --perf, --json" in result.stderr


def test_a_refused_combination_starts_nothing(environment, prepared_runner):
    debugged("--perf")
    assert prepared_runner.scopes == []


def test_no_time_limit_is_harmless_with_debug(environment):
    assert debugged("--no-time-limit").exit_code == ExitCode.SUCCESS


@pytest.mark.parametrize("option", [["--debug-port", "6000"], ["--debug-connect"]])
def test_debug_options_need_debug(environment, option):
    result = invoke(*option)
    assert (result.exit_code, f"error: {option[0]} needs --debug" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


@pytest.mark.parametrize("port", ["0", "65536", "-1"])
def test_ports_outside_the_range_are_usage_errors(environment, port):
    assert debugged("--debug-port", port).exit_code == ExitCode.USAGE_ERROR


def test_connecting_is_only_for_the_jvm(environment):
    result = debugged("--debug-connect")
    assert (result.exit_code, "--debug-connect is only for java and kotlin" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_the_session_uses_the_requested_port(environment, prepared_runner):
    debugged("--debug-port", "6000")
    scope = prepared_runner.scopes[-1]
    assert isinstance(scope, UserCode)
    assert scope.debug is not None
    assert scope.debug.port == 6000


def test_the_ready_line_goes_to_standard_error(environment):
    assert READY_LINE in debugged().stderr.splitlines()


def test_the_ready_line_is_the_only_one_and_plain(environment):
    assert debugged().stderr.splitlines().count(READY_LINE) == 1


def test_the_report_does_not_hold_the_ready_line(environment):
    assert READY_LINE not in debugged().stdout


def test_notices_go_to_standard_error_too(environment):
    assert "computing expected values" in debugged().stderr


def test_a_passing_debug_run_exits_0(environment):
    assert debugged().exit_code == ExitCode.SUCCESS


def test_the_report_names_the_debug_run_and_shows_no_timings(environment):
    assert report_lines(debugged()) == [
        "two-sum · python · debug · 4 cases (2 visible, 1 hidden, 1 generated)",
        "",
        "PASS     ex1",
        "PASS     ex2",
        "PASS     2 hidden cases",
        "",
        "4/4 passed",
        "all passed (debug run: not recorded; cstudy test records the run)",
    ]


def test_a_normal_run_keeps_its_timings(environment):
    assert TIMING.search(invoke().stdout) is not None


def test_a_debug_run_is_not_recorded(environment):
    debugged()
    attempt = environment.progress.active_attempt()
    assert environment.progress.latest_test_run(attempt.id) is None


def test_failures_exit_1_and_still_show_no_total(tmp_path, monkeypatch, prepared_runner):
    process = AnnouncingProcess()
    process.answer = wrong
    started_environment(tmp_path, monkeypatch, prepared_runner, process)
    result = debugged("--case", "ex1")
    assert (result.exit_code, "0/1 passed · 1 failed" in report_lines(result)) == (
        ExitCode.FAILURES,
        True,
    )


def test_ctrl_c_exits_130(tmp_path, monkeypatch, prepared_runner):
    started_environment(tmp_path, monkeypatch, prepared_runner, AnnouncingProcess(interrupted=True))
    assert debugged().exit_code == ExitCode.INTERRUPTED
