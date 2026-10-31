"""`cstudy test` on a project problem: the native suite's report and JSON document
(docs/specs/cli.md#project-problems)."""

import json
import re
from dataclasses import replace
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.runs import Crashed, Raised, TimedOut, UserError
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Comparison,
    Passed,
    Skipped,
    SuiteReport,
    SuiteTest,
)
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.project_fakes import (
    LEVEL_1_TEST,
    PROJECT_FOLDER,
    PROJECT_RUNNER,
    PROJECT_SLUG,
    ScriptedProjectProcess,
    project_environment,
)

runner = CliRunner()
TIMING = re.compile(r"\d+\.\d+s")
FAILED = SuiteTest(
    "tests/test_level_1.py::test_ex2",
    AssertionFailed("assert -1 == 5", 1000, comparison=Comparison(5, -1)),
)
YOURS = SuiteTest("tests/test_overdraft.py::test_refuses_overdraft", Passed(1000))
STARTER = SuiteTest("README.md::test_readme", Passed(1000))
SKIPPED = SuiteTest("tests/test_overdraft.py::test_later", Skipped("not yet", 0))
ERROR = UserError("KeyError", "'ivy'", 'File "bank/bank.py", line 9')


@pytest.fixture
def process() -> ScriptedProjectProcess:
    return ScriptedProjectProcess()


@pytest.fixture
def environment(tmp_path, monkeypatch, process):
    environment = project_environment(tmp_path, process)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    return environment


def cs_test(*arguments: str):
    return runner.invoke(cli.app, ["test", *arguments])


def lines(*arguments: str) -> list[str]:
    return [TIMING.sub("T", line) for line in cs_test(*arguments).output.splitlines()]


def document(*arguments: str) -> dict:
    return json.loads(cs_test("--json", *arguments).stdout)


def test_a_passing_suite_points_to_cstudy_submit(environment):
    assert lines() == [
        f"{PROJECT_SLUG} · python · level 1 of 2",
        "suite  pytest, T",
        "",
        "PASS     tests/test_level_1.py::test_ex1",
        "",
        "1/1 passed · total T",
        "all passed. Next: cstudy submit",
    ]


def test_a_passing_suite_exits_0(environment):
    assert cs_test().exit_code == ExitCode.SUCCESS


def test_a_failing_test_shows_the_frameworks_message_then_expected_and_actual(environment, process):
    process.tests = (LEVEL_1_TEST, FAILED)
    assert lines()[4:9] == [
        "FAIL     tests/test_level_1.py::test_ex2",
        "         assert -1 == 5",
        "         expected  5",
        "         actual    -1",
        "",
    ]


def test_a_failing_suite_exits_1(environment, process):
    process.tests = (FAILED,)
    assert cs_test().exit_code == ExitCode.FAILURES


def test_the_summary_counts_the_tests_that_ran(environment, process):
    process.tests = (LEVEL_1_TEST, FAILED, SKIPPED)
    assert lines()[-1] == "1/2 passed · total T"


def test_your_tests_and_the_starters_are_tagged(environment, process):
    process.tests = (YOURS, STARTER)
    assert lines()[3:5] == [
        "PASS     tests/test_overdraft.py::test_refuses_overdraft   yours",
        "PASS     README.md::test_readme   starter",
    ]


def test_an_error_shows_the_exception_and_its_trace(environment, process):
    process.tests = (SuiteTest("tests/test_level_1.py::test_ex1", Raised(ERROR, 1000)),)
    assert lines()[3:6] == [
        "ERROR    tests/test_level_1.py::test_ex1",
        "         error     KeyError: 'ivy'",
        '                   File "bank/bank.py", line 9',
    ]


def test_a_skipped_test_shows_its_reason(environment, process):
    process.tests = (LEVEL_1_TEST, SKIPPED)
    assert lines()[4:6] == [
        "SKIP     tests/test_overdraft.py::test_later   yours",
        "         reason    not yet",
    ]


def test_a_hung_test_shows_the_hang_guard(environment, process):
    process.tests = (SuiteTest("tests/test_level_1.py::test_ex1", TimedOut(10_000)),)
    assert lines()[3:5] == [
        "TIMEOUT  tests/test_level_1.py::test_ex1",
        "         limit     10000 ms hang guard",
    ]


def test_a_crash_shows_the_runners_exit(environment, process):
    process.tests = (SuiteTest("tests/test_level_1.py::test_ex1", Crashed(139, ("boom",))),)
    assert lines()[3:6] == [
        "ERROR    tests/test_level_1.py::test_ex1",
        "         crash     runner exited with code 139",
        "                   boom",
    ]


def test_a_run_without_tests_says_so(environment, process):
    process.tests = ()
    assert lines()[-1] == "no tests ran · total T"


def test_a_run_without_tests_exits_1(environment, process):
    process.tests = ()
    assert cs_test().exit_code == ExitCode.FAILURES


def test_a_suite_stopped_early_says_why(environment, process, monkeypatch):
    stopped = SuiteReport(PROJECT_RUNNER, (LEVEL_1_TEST,), stopped_early="restarts ran out")
    monkeypatch.setattr(process, "run_suite", lambda launch, job: stopped)
    assert "NOT RUN  restarts ran out" in lines()


def test_a_suite_that_could_not_run_shows_the_frameworks_error(environment, process, monkeypatch):
    failed = SuiteReport(PROJECT_RUNNER, load_error=UserError("UsageError", "bad addopts"))
    monkeypatch.setattr(process, "run_suite", lambda launch, job: failed)
    assert lines()[3] == "ERROR    load  UsageError: bad addopts"


def test_a_selection_of_tests_does_not_point_to_submit(environment):
    assert lines("--case", "test_ex1")[-1] == "all selected tests passed"


def test_a_case_that_matches_nothing_exits_3(environment):
    result = cs_test("--case", "test_zz")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: no test matches --case test_zz\n",
    )


def test_a_locked_level_exits_3_naming_submit(environment):
    result = cs_test("--level", "2")
    assert result.stderr == "error: level 2 is locked; pass level 1 with cstudy submit first\n"


@pytest.mark.parametrize(
    ("arguments", "option"),
    [
        (("--perf",), "--perf"),
        (("--stress", "3"), "--stress"),
        (("--time-limit",), "--time-limit"),
        (("--debug", "--debug-connect"), "--debug-connect"),
    ],
)
def test_options_without_meaning_for_a_project_exit_3(environment, arguments, option):
    result = cs_test(*arguments)
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        f"error: {option} is not available for project problems\n",
    )


def test_all_is_accepted_and_changes_nothing(environment):
    assert lines("--all") == lines()


def test_the_header_shows_the_timer(environment):
    attempt = environment.progress.active_attempt()
    environment.progress.update_attempt(replace(attempt, time_limit_s=5400))
    environment.clock.advance(timedelta(minutes=31, seconds=40))
    assert lines()[0] == f"{PROJECT_SLUG} · python · level 1 of 2 · timer 31:40 / 90:00"


def test_watch_watches_the_project_folder(environment):
    cs_test("--watch")
    assert environment.watcher.watched == [environment.workspace.absolute(PROJECT_FOLDER)]


def test_json_describes_the_run(environment):
    found = document()
    assert {key: found[key] for key in ("slug", "outcome", "exit_code", "every_case")} == {
        "slug": PROJECT_SLUG,
        "outcome": "passed",
        "exit_code": 0,
        "every_case": True,
    }


def test_json_has_no_comparator_oracle_or_stress(environment):
    found = document()
    assert (found["comparator"], found["oracle"], found["stress"]) == (None, None, [])


def test_json_levels_never_open_one(environment):
    assert document()["levels"] == {
        "ran_up_to": 1,
        "last": 2,
        "unlocked": 1,
        "newly_unlocked": False,
    }


def test_json_lists_each_test_with_its_origin_and_level(environment, process):
    process.tests = (LEVEL_1_TEST, YOURS)
    assert document()["cases"] == [
        {
            "id": "tests/test_level_1.py::test_ex1",
            "status": "pass",
            "duration_ns": 1000,
            "origin": "level",
            "level": 1,
        },
        {
            "id": "tests/test_overdraft.py::test_refuses_overdraft",
            "status": "pass",
            "duration_ns": 1000,
            "origin": "yours",
            "level": None,
        },
    ]


def test_json_shows_a_failures_message_expected_and_actual(environment, process):
    process.tests = (FAILED,)
    (found,) = document()["cases"]
    assert (found["message"], found["expected"], found["actual"]) == ("assert -1 == 5", 5, -1)


def test_json_tallies_the_tests(environment, process):
    process.tests = (LEVEL_1_TEST, FAILED, SKIPPED)
    assert document()["tally"] == {
        "total": 2,
        "passed": 1,
        "failed": 1,
        "errored": 0,
        "timed_out": 0,
        "tle": 0,
    }


def test_json_with_watch_is_a_usage_error(environment):
    assert cs_test("--json", "--watch").exit_code == ExitCode.USAGE_ERROR


def test_a_debug_run_names_itself_and_shows_no_durations(environment):
    assert lines("--debug") == [
        f"{PROJECT_SLUG} · python · debug · level 1 of 2",
        "",
        "PASS     tests/test_level_1.py::test_ex1",
        "",
        "1/1 passed",
        "all passed (debug run: not recorded; cstudy test records the run)",
    ]
