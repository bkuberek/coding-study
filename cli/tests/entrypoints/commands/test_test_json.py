"""`cstudy test --json` (docs/specs/cli.md#json-output)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.concurrency_fakes import duplicating
from tests.e2e import e2e_environment
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
)
from tests.helpers import CONCURRENCY_PROBLEMS

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
SOLUTIONS = PRACTICE / "0001-two-sum" / "solutions"
STUB = "python/practice/two_sum.py"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PRACTICE))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


def solve(environment, body: str | None = None) -> None:
    text = body if body is not None else (SOLUTIONS / "hash-map.py").read_text()
    environment.workspace.write_text(STUB, text)


def document(*arguments: str) -> dict:
    result = runner.invoke(cli.app, ["test", "--json", *arguments])
    return json.loads(result.stdout)


def case(found: dict, case_id: str) -> dict:
    return next(entry for entry in found["cases"] if entry["id"] == case_id)


def test_json_names_the_problem_and_the_outcome(environment):
    solve(environment)
    found = document()
    assert (found["slug"], found["language"], found["outcome"], found["exit_code"]) == (
        "two-sum",
        "python",
        "passed",
        0,
    )


def test_json_exits_like_the_text_report(environment):
    solve(environment, "def two_sum(nums, target):\n    return [3, 3]\n")
    result = runner.invoke(cli.app, ["test", "--json", "--case", "ex1"])
    assert result.exit_code == ExitCode.FAILURES


def test_json_tallies_the_run(environment):
    solve(environment)
    assert document()["tally"] == {
        "total": 4,
        "passed": 4,
        "failed": 0,
        "errored": 0,
        "timed_out": 0,
        "tle": 0,
    }


def test_json_lists_passing_hidden_cases_too(environment):
    solve(environment)
    assert [entry["id"] for entry in document()["cases"]] == ["ex1", "ex2", "h1", "g1"]


def test_a_passing_case_has_its_status_and_duration(environment):
    solve(environment)
    found = case(document(), "ex1")
    assert (sorted(found), found["status"]) == (
        ["duration_ns", "generated", "id", "status", "visible"],
        "pass",
    )


def test_a_failing_case_shows_input_expected_and_actual(environment):
    solve(environment, "def two_sum(nums, target):\n    return [3, 3]\n")
    found = case(document("--case", "h1"), "h1")
    assert {key: found[key] for key in ("status", "input", "expected", "actual", "note")} == {
        "status": "fail",
        "input": {"nums": [-3, 8, 0, 3], "target": 0},
        "expected": [0, 3],
        "actual": [3, 3],
        "note": "negatives and zero",
    }


def test_json_names_the_comparator(environment):
    solve(environment)
    assert document()["comparator"] == "unordered"


def test_an_exception_shows_the_error(environment):
    solve(environment, "def two_sum(nums, target):\n    raise ValueError('no pair')\n")
    error = case(document("--case", "ex1"), "ex1")["error"]
    assert (error["type"], error["message"]) == ("ValueError", "no pair")


def test_printed_output_is_kept(environment):
    solve(environment, "def two_sum(nums, target):\n    print('debug')\n    return []\n")
    assert case(document("--case", "ex1"), "ex1")["stdout"] == "debug\n"


def test_code_that_does_not_load_reports_the_load_error(environment):
    solve(environment, "def other():\n    pass\n")
    found = document()
    assert (found["outcome"], found["exit_code"], found["load_error"]["type"]) == (
        "load_failed",
        ExitCode.USER_CODE_ERROR,
        "AttributeError",
    )


def test_json_records_the_time_limit_off(environment):
    solve(environment)
    assert document()["time_limit"] is None


def test_notices_go_to_standard_error(environment):
    solve(environment)
    result = runner.invoke(cli.app, ["test", "--json"])
    assert "computing expected values" in result.stderr


def test_json_with_watch_is_a_usage_error(environment):
    result = runner.invoke(cli.app, ["test", "--json", "--watch"])
    assert result.exit_code == ExitCode.USAGE_ERROR


def test_json_with_perf_is_a_usage_error(environment):
    result = runner.invoke(cli.app, ["test", "--json", "--perf"])
    assert result.exit_code == ExitCode.USAGE_ERROR


@pytest.fixture
def concurrent(tmp_path, monkeypatch):
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    environment = make_environment(
        repository_root(tmp_path, CONCURRENCY_PROBLEMS),
        toolchains=toolchains,
        runner_process=ScriptedRunnerProcess(duplicating),
    )
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("bounded-blocking-queue", Language.PYTHON))
    return environment


def test_a_stress_case_has_the_specified_shape(concurrent):
    stress = document("--case", "s1", "--stress", "2")["stress"]
    assert stress == [
        {
            "id": "s1",
            "variant": "thread",
            "status": "fail",
            "runs": 2,
            "runs_passed": 0,
            "median_ms": stress[0]["median_ms"],
            "failures": [
                {
                    "run": 0,
                    "seed": 1000,
                    "status": "fail",
                    "reasons": [
                        "equal_multisets put.arg0 vs take: 1 missing (1000000), 1 extra (0)",
                        "distinct take: 0 (2 times)",
                    ],
                },
                {
                    "run": 1,
                    "seed": 1001,
                    "status": "fail",
                    "reasons": stress[0]["failures"][1]["reasons"],
                },
            ],
        }
    ]
