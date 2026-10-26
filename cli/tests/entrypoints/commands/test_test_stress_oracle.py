"""`cstudy test --stress N` for problems that are not concurrent: N generated inputs checked against
the oracle approach (docs/specs/cli.md#oracle-inputs)."""

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptStatus, Rating
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import repository_root

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"
SOLUTIONS = PRACTICE / "0001-two-sum" / "solutions"
STUB = "python/practice/two_sum.py"
TIMING = re.compile(r"\d+(\.\d+)?(ms|s)")
SMALL_INPUTS_WRONG = (
    "def two_sum(nums, target):\n"
    "    if len(nums) < 12:\n"
    "        return [0, 0]\n"
    "    seen = {}\n"
    "    for index, value in enumerate(nums):\n"
    "        if target - value in seen:\n"
    "            return [seen[target - value], index]\n"
    "        seen[value] = index\n"
    "    return []\n"
)
"""Wrong on fewer than 12 numbers, so it fails some small oracle inputs and passes others."""


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PRACTICE))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


def solve(environment, body: str | None = None) -> None:
    text = body if body is not None else (SOLUTIONS / "hash-map.py").read_text()
    environment.workspace.write_text(STUB, text)


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["test", *arguments])


def lines(*arguments: str) -> list[str]:
    return [TIMING.sub("T", line) for line in invoke(*arguments).output.splitlines()]


def warmed(*arguments: str) -> list[str]:
    """The second run's lines, once generated and oracle values are cached."""
    invoke(*arguments)
    return lines(*arguments)


def test_a_correct_solution_passes_every_oracle_input(environment):
    solve(environment)
    assert warmed("--stress", "20") == [
        "two-sum · python · 4 cases (2 visible, 1 hidden, 1 generated) · "
        "20 oracle inputs (seeds 1-20)",
        "",
        "PASS     ex1        T",
        "PASS     ex2        T",
        "PASS     2 hidden cases",
        "PASS     20 oracle inputs",
        "",
        "24/24 passed · total T",
        "all passed. Next: cstudy done --rating easy|ok|hard",
    ]


def test_a_correct_solution_exits_0(environment):
    solve(environment)
    assert invoke("--stress", "5").exit_code == ExitCode.SUCCESS


def test_oracle_outputs_are_computed_once(environment):
    solve(environment)
    first, second = invoke("--stress", "5"), invoke("--stress", "5")
    notice = "computing oracle outputs for the stress inputs (one-time)"
    assert (notice in first.output, notice in second.output) == (True, False)


def test_more_inputs_compute_only_the_new_outputs(environment):
    solve(environment)
    invoke("--stress", "5")
    notice = "computing oracle outputs for the stress inputs (one-time)"
    assert notice in invoke("--stress", "6").output


def test_a_wrong_answer_on_an_oracle_input_fails_the_run(environment):
    solve(environment, "def two_sum(nums, target):\n    return [0, 1]\n")
    assert invoke("--stress", "10").exit_code == ExitCode.FAILURES


def test_failing_oracle_inputs_show_the_smallest_three(environment):
    solve(environment, SMALL_INPUTS_WRONG)
    output = warmed("--stress", "30")
    shown = [line.split()[1] for line in output if line.startswith("FAIL     oracle-")]
    sizes = [int(line.rsplit("n=", 1)[1]) for line in output if line.startswith("FAIL     oracle-")]
    assert (len(shown), sizes == sorted(sizes)) == (3, True)


def test_a_failing_oracle_input_shows_input_expected_and_actual(environment):
    solve(environment, "def two_sum(nums, target):\n    return [0, 0]\n")
    output = warmed("--case", "ex1", "--stress", "1", "--seed", "4")
    block = output[output.index(next(line for line in output if "oracle-4" in line)) :]
    assert [line.split()[0] for line in block[:4]] == ["FAIL", "input", "expected", "actual"]


def test_the_expected_value_names_the_oracle(environment):
    solve(environment, "def two_sum(nums, target):\n    return [0, 0]\n")
    output = warmed("--case", "ex1", "--stress", "1")
    expected = next(line for line in output if "expected" in line and "oracle" in line)
    assert expected.endswith("(unordered, oracle brute-force)")


def test_more_failures_than_shown_are_counted(environment):
    solve(environment, "def two_sum(nums, target):\n    return [0, 0]\n")
    assert "         7 more oracle inputs did not pass" in warmed("--stress", "10")


def test_the_summary_counts_oracle_inputs(environment):
    solve(environment, "def two_sum(nums, target):\n    return [0, 0]\n")
    summary = warmed("--case", "ex1", "--stress", "10")[-1]
    assert summary.startswith("0/11 passed · 11 failed")


def test_seed_chooses_the_first_input(environment):
    solve(environment)
    invoke("--json", "--stress", "2", "--seed", "7")
    document = json.loads(invoke("--json", "--stress", "2", "--seed", "7").stdout)
    assert [entry["id"] for entry in document["oracle"]["inputs"]] == ["oracle-7", "oracle-8"]


def test_json_lists_each_oracle_input_with_its_seed_and_size(environment):
    solve(environment)
    invoke("--stress", "1", "--seed", "3")
    document = json.loads(invoke("--json", "--stress", "1", "--seed", "3").stdout)
    entry = document["oracle"]["inputs"][0]
    assert (entry["seed"], entry["status"], document["oracle"]["approach"]) == (
        3,
        "pass",
        "brute-force",
    )


def test_json_keeps_oracle_inputs_out_of_the_cases(environment):
    solve(environment)
    invoke("--stress", "2")
    document = json.loads(invoke("--json", "--stress", "2").stdout)
    assert [entry["id"] for entry in document["cases"]] == ["ex1", "ex2", "h1", "g1"]


def test_json_without_stress_has_no_oracle(environment):
    solve(environment)
    invoke()
    assert json.loads(invoke("--json").stdout)["oracle"] is None


def test_the_test_run_leaves_oracle_inputs_out(environment):
    solve(environment)
    invoke("--stress", "3")
    attempt = environment.progress.active_attempt()
    assert environment.progress.latest_test_run(attempt.id).tally.total == 4


def test_a_full_pass_with_oracle_inputs_sets_the_first_pass(environment):
    solve(environment)
    invoke("--stress", "3")
    assert environment.progress.active_attempt().first_pass_at is not None


def test_done_takes_a_rating_after_a_full_pass_with_oracle_inputs(environment):
    solve(environment)
    invoke("--stress", "3")
    finished = complete_attempt(environment, DoneRequest(rating=Rating.OK))
    assert finished.attempt.status is AttemptStatus.PASSED


def test_a_failing_oracle_input_exits_1_but_stores_the_passing_cases(environment):
    solve(environment, SMALL_INPUTS_WRONG.replace("len(nums) < 12", "len(nums) in (3, 5, 6)"))
    result = invoke("--stress", "30")
    attempt = environment.progress.active_attempt()
    tally = environment.progress.latest_test_run(attempt.id).tally
    assert (result.exit_code, tally.all_passed) == (ExitCode.FAILURES, True)


def test_seed_without_stress_is_a_usage_error(environment):
    solve(environment)
    result = invoke("--seed", "3")
    assert (result.exit_code, "--seed needs --stress" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_a_problem_without_a_generator_has_no_oracle_inputs(environment):
    start_attempt(environment, StartRequest("lru-cache"))
    result = invoke("lru-cache", "--stress", "5")
    assert (result.exit_code, "generator.py" in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_a_progressive_problem_has_no_oracle_inputs(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PHASE4))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("level-store"))
    result = invoke("--stress", "5")
    assert (result.exit_code, "progressive" in result.stderr) == (ExitCode.USAGE_ERROR, True)
