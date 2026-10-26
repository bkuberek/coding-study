import re
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import ScriptedWatcher, repository_root

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
SOLUTIONS = PRACTICE / "0001-two-sum" / "solutions"
STUB = "python/practice/two_sum.py"
LRU_STUB = "python/practice/lru_cache.py"
TIMING = re.compile(r"\d+(\.\d+)?(ms|s)")


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PRACTICE))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


def solve(environment, solution: str = "hash-map") -> None:
    environment.workspace.write_text(STUB, (SOLUTIONS / f"{solution}.py").read_text())


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["test", *arguments])


def lines(result) -> list[str]:
    """Output lines with timings replaced by `T`."""
    return [TIMING.sub("T", line) for line in result.output.splitlines()]


def test_passing_solution_exits_0(environment):
    solve(environment)
    assert invoke().exit_code == 0


def warmed(*arguments: str):
    """The second run's result, once generated expected values are cached."""
    invoke(*arguments)
    return invoke(*arguments)


def test_passing_report(environment):
    solve(environment)
    assert lines(warmed()) == [
        "two-sum · python · 4 cases (2 visible, 1 hidden, 1 generated)",
        "",
        "PASS     ex1   T",
        "PASS     ex2   T",
        "PASS     2 hidden cases",
        "",
        "4/4 passed · total T",
        "all passed. Next: cstudy done --rating easy|ok|hard",
    ]


def test_computing_generated_expected_values_is_announced_once(environment):
    solve(environment)
    first, second = invoke(), invoke()
    notice = "computing expected values for generated cases (one-time)"
    assert (notice in first.output, notice in second.output) == (True, False)


def test_all_lists_passing_hidden_cases(environment):
    solve(environment)
    assert lines(warmed("--all"))[4:6] == ["PASS     h1    hidden · T", "PASS     g1    hidden · T"]


def test_failing_hidden_case_reveals_input_expected_and_actual(environment):
    environment.workspace.write_text(STUB, "def two_sum(nums, target):\n    return [3, 3]\n")
    assert lines(invoke("--case", "h1")) == [
        "two-sum · python · 1 case (0 visible, 1 hidden, 0 generated)",
        "",
        "FAIL     h1    hidden",
        "         input     nums=[-3, 8, 0, 3]  target=0",
        "         expected  [0, 3]  (unordered)",
        "         actual    [3, 3]",
        "         note      negatives and zero",
        "",
        "0/1 passed · 1 failed · total T",
    ]


def test_failures_exit_1(environment):
    environment.workspace.write_text(STUB, "def two_sum(nums, target):\n    return [3, 3]\n")
    assert invoke("--case", "ex1").exit_code == ExitCode.FAILURES


def test_exception_shows_the_error(environment):
    environment.workspace.write_text(
        STUB, "def two_sum(nums, target):\n    raise ValueError('no pair')\n"
    )
    assert lines(invoke("--case", "ex1"))[2:5] == [
        "ERROR    ex1",
        "         input     nums=[4, 9, 2, 8]  target=11",
        "         error     ValueError: no pair",
    ]


def test_printed_output_of_a_failing_case_is_shown(environment):
    environment.workspace.write_text(
        STUB, "def two_sum(nums, target):\n    print('debug', nums)\n    return []\n"
    )
    assert "         stdout    debug [4, 9, 2, 8]" in lines(invoke("--case", "ex1"))


def test_stub_that_does_not_load_exits_2(environment):
    environment.workspace.write_text(STUB, "def two_sum(:\n")
    result = invoke("--case", "ex1")
    assert (result.exit_code, lines(result)[2].startswith("ERROR    load")) == (
        ExitCode.USER_CODE_ERROR,
        True,
    )


def test_the_generated_stub_fails_every_case(environment):
    assert lines(invoke())[-1] == "0/4 passed · 4 errors · total T"


def test_unknown_case_is_a_usage_error(environment):
    assert invoke("--case", "h9").exit_code == ExitCode.USAGE_ERROR


def test_without_an_attempt_is_a_usage_error(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PRACTICE))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    assert invoke().stderr == "error: no attempt in progress; start one with cstudy start <slug>\n"


def test_selected_cases_passing_do_not_suggest_done(environment):
    solve(environment)
    assert lines(invoke("--case", "ex1"))[-1] == "all selected cases passed"


def test_timer_is_shown_in_the_header(environment):
    attempt = environment.progress.active_attempt()
    environment.progress.update_attempt(replace(attempt, time_limit_s=1500))
    solve(environment)
    assert lines(invoke("--case", "ex1"))[0].endswith("· timer 00:00 / 25:00")


def test_design_problem_reports_the_failing_operation(environment):
    start_attempt(environment, StartRequest("lru-cache", Language.PYTHON))
    source = (PRACTICE / "0002-lru-cache/solutions/ordered-dict.py").read_text()
    environment.workspace.write_text(LRU_STUB, source.replace("return -1", "return 0"))
    assert lines(invoke("lru-cache", "--case", "h1"))[2:7] == [
        "FAIL     h1    hidden",
        '         input     ops=["LRUCache", "get", "put", "get"]  args=[[1], [5], [5, 7], [5]]',
        "         expected  [null, -1, null, 7]",
        "         actual    [null, 0, null, 7]",
        "         reason    op 1 get: expected -1, got 0",
    ]


def test_design_problem_exception_shows_the_operations_so_far(environment):
    start_attempt(environment, StartRequest("lru-cache", Language.PYTHON))
    assert lines(invoke("lru-cache", "--case", "ex1"))[2:6] == [
        "ERROR    ex1",
        '         input     ops=["LRUCache", "put"]  args=[[2], [1, 1]]',
        "         error     NotImplementedError",
        "         outputs   [null]",
    ]


def test_watch_reruns_after_each_save(environment, monkeypatch):
    watcher = ScriptedWatcher(bursts=2)
    watching = replace(environment, watcher=watcher)
    monkeypatch.setattr(test_command, "load_environment", lambda *_: watching)
    solve(environment)
    assert invoke("--watch", "--case", "ex1").output.count("PASS     ex1") == 3


def test_watch_watches_the_user_file(environment, monkeypatch):
    watcher = ScriptedWatcher()
    watching = replace(environment, watcher=watcher)
    monkeypatch.setattr(test_command, "load_environment", lambda *_: watching)
    invoke("--watch", "--case", "ex1")
    assert watcher.watched == [environment.root / STUB]


def test_watch_keeps_going_after_an_error(environment, monkeypatch):
    watching = replace(environment, watcher=ScriptedWatcher(bursts=1))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: watching)
    (environment.root / "problems/0001-two-sum/generator.py").write_text("import nope\n")
    result = invoke("--watch")
    assert result.stderr.count("error: problems/0001-two-sum/generator.py") == 2


def test_interrupting_watch_exits_130(environment, monkeypatch):
    class Interrupted(ScriptedWatcher):
        def changes(self, path):
            raise KeyboardInterrupt
            yield

    watching = replace(environment, watcher=Interrupted())
    monkeypatch.setattr(test_command, "load_environment", lambda *_: watching)
    assert invoke("--watch", "--case", "ex1").exit_code == ExitCode.INTERRUPTED


SLOW_SOLUTION = (
    "import time\n\ndef two_sum(nums, target):\n    time.sleep(0.15)\n    return [1, 2]\n"
)


def test_time_limit_is_shown_in_the_header(environment):
    solve(environment)
    assert lines(invoke("--time-limit=1500ms", "--case", "ex1"))[0].endswith("· time limit T")


def test_time_limits_are_off_without_the_flag(environment):
    solve(environment)
    assert "time limit" not in invoke("--case", "ex1").output


def test_case_over_the_time_limit_is_reported_tle(environment):
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    assert lines(invoke("--time-limit=20ms", "--case", "ex1"))[2:5] == [
        "TLE      ex1   T > limit T",
        "",
        "0/1 passed · 1 tle · total T",
    ]


def test_tle_exits_1(environment):
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    assert invoke("--time-limit=20ms", "--case", "ex1").exit_code == ExitCode.FAILURES


def test_bare_time_limit_flag_keeps_the_slug_argument(environment):
    solve(environment)
    result = invoke("--time-limit", "two-sum", "--case", "ex1")
    assert lines(result)[-3:] == ["", "1/1 passed · total T", "all selected cases passed"]


def test_bare_time_limit_flag_calibrates_the_default_factor(environment):
    solve(environment)
    output = invoke("--time-limit", "--case", "ex1").output
    assert ("calibrating time limits (one-time)" in output, "· time limit 5x" in output) == (
        True,
        True,
    )


def test_calibrated_tle_names_the_limit_basis(environment):
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    assert (
        lines(invoke("--case", "ex1", "--time-limit"))[-3] == "TLE      ex1   T > limit T (floor)"
    )


def test_invalid_time_limit_is_a_usage_error(environment):
    result = invoke("--time-limit=fast")
    assert (result.exit_code, "invalid time limit" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_time_limit_and_no_time_limit_exclude_each_other(environment):
    assert invoke("--time-limit", "--no-time-limit").exit_code == ExitCode.USAGE_ERROR


def test_no_time_limit_runs_without_limits(environment):
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    assert invoke("--no-time-limit", "--case", "ex1").exit_code == ExitCode.SUCCESS


def test_a_solution_file_path_targets_its_problem_and_language(environment):
    solve(environment)
    result = invoke(str(environment.root / STUB))
    assert (result.exit_code, "two-sum · python · 4 cases" in result.output) == (0, True)


def test_a_relative_solution_file_path_resolves_against_the_working_directory(
    environment, monkeypatch
):
    solve(environment)
    monkeypatch.chdir(environment.root / "python")
    assert invoke("practice/two_sum.py").exit_code == 0


def test_a_path_to_another_problem_targets_that_problem(environment):
    result = invoke(str(environment.root / LRU_STUB))
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: no attempt in progress for lru-cache in python; "
        "start one with cstudy start lru-cache --lang python\n",
    )


def test_a_path_in_another_language_than_the_option_exits_3(environment):
    path = str(environment.root / STUB)
    result = invoke(path, "--lang", "kotlin")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        f"error: {path} is a python file but --lang kotlin was given\n",
    )


def test_a_path_outside_the_workspace_exits_3(environment, tmp_path_factory):
    outside = tmp_path_factory.mktemp("elsewhere") / STUB
    result = invoke(str(outside))
    assert (result.exit_code, "not a solution file in this workspace" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )
