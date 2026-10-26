"""`cstudy test --debug`: a judged run the IDE debugger can step through
(docs/specs/cli.md#cstudy-test)."""

from pathlib import Path

import pytest

from coding_study.application.run_tests import RunTestsRequest, run_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.time_limits import TimeLimitFlags
from coding_study.domain.debugging import DebugRequest, DebugSession
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.domain.time_limits import parse_time_limit
from tests.concurrency_fakes import queue
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
    two_sum,
)
from tests.helpers import CONCURRENCY_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STRESS_SKIPPED = "stress runs are skipped while debugging"


def started(tmp_path: Path, problems: Path, process: ScriptedRunnerProcess, slug: str):
    runner = FakeLanguageRunner()
    toolchains = FakeToolchains({Language.PYTHON: runner}, {Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, problems), toolchains=toolchains, runner_process=process
    )
    start_attempt(environment, StartRequest(slug, Language.PYTHON))
    return environment, runner


@pytest.fixture
def two_sum_run(tmp_path):
    return started(tmp_path, PRACTICE, ScriptedRunnerProcess(two_sum), "two-sum")


def debugged(environment, notices: list[str] | None = None, **fields):
    request = RunTestsRequest(debug=DebugRequest(), **fields)
    return run_tests(environment, request, (notices if notices is not None else []).append)


def test_the_user_code_is_prepared_for_the_languages_debug_session(two_sum_run):
    environment, runner = two_sum_run
    debugged(environment)
    assert runner.scopes[-1].debug == DebugSession(Language.PYTHON, 5678)


def test_the_result_carries_the_debug_session(two_sum_run):
    environment, _ = two_sum_run
    assert debugged(environment).debug == DebugSession(Language.PYTHON, 5678)


def test_an_explicit_port_reaches_the_session(two_sum_run):
    environment, _ = two_sum_run
    result = run_tests(
        environment, RunTestsRequest(debug=DebugRequest(port=6000)), lambda _line: None
    )
    assert result.debug == DebugSession(Language.PYTHON, 6000)


def test_connecting_to_the_ide_is_only_for_the_jvm(two_sum_run):
    environment, _ = two_sum_run
    request = RunTestsRequest(debug=DebugRequest(connect=True))
    with pytest.raises(UsageError, match="--debug-connect is only for java and kotlin"):
        run_tests(environment, request, lambda _line: None)


def test_a_normal_run_prepares_no_debug_session(two_sum_run):
    environment, runner = two_sum_run
    run_tests(environment, RunTestsRequest(), lambda _line: None)
    assert runner.scopes[-1].debug is None


def test_the_run_is_judged_like_any_other(two_sum_run):
    environment, _ = two_sum_run
    assert debugged(environment).passed


def test_a_debug_run_is_not_recorded(two_sum_run):
    environment, _ = two_sum_run
    result = debugged(environment)
    assert environment.progress.latest_test_run(result.attempt.id) is None


def test_a_passing_debug_run_is_no_first_pass(two_sum_run):
    environment, _ = two_sum_run
    debugged(environment)
    assert environment.progress.active_attempt().first_pass_at is None


def test_time_limits_are_off_even_when_asked_for(two_sum_run):
    environment, _ = two_sum_run
    flags = TimeLimitFlags(enabled=True, value=parse_time_limit("1500ms"))
    assert debugged(environment, time_limits=flags).time_limits is None


def test_time_limits_apply_to_a_normal_run_with_the_same_flags(two_sum_run):
    environment, _ = two_sum_run
    flags = TimeLimitFlags(enabled=True, value=parse_time_limit("1500ms"))
    request = RunTestsRequest(time_limits=flags)
    assert run_tests(environment, request, lambda _line: None).time_limits is not None


@pytest.fixture
def queue_run(tmp_path):
    process = ScriptedRunnerProcess(queue)
    environment, _ = started(tmp_path, CONCURRENCY_PROBLEMS, process, "bounded-blocking-queue")
    return environment, process


def test_stress_runs_are_left_out_of_a_debug_run(queue_run):
    environment, process = queue_run
    debugged(environment)
    ids = [case.id for case in process.requests[-1].jobs[0].cases]
    assert ids == ["ex1", "ex2", "h1", "h2", "h3", "h4"]


def test_skipping_stress_runs_is_announced(queue_run):
    environment, _ = queue_run
    notices: list[str] = []
    debugged(environment, notices)
    assert notices == [STRESS_SKIPPED]


def test_a_problem_without_stress_runs_announces_no_skipping(two_sum_run):
    environment, _ = two_sum_run
    notices: list[str] = []
    debugged(environment, notices)
    assert STRESS_SKIPPED not in notices


def test_the_stress_plan_of_a_debug_run_is_empty(queue_run):
    environment, _ = queue_run
    assert debugged(environment).stress_plan == ()
