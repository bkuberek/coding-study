import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.ports import BuildFailed
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.bench_runs import USER_TARGET_ID
from coding_study.domain.problem import Language
from coding_study.domain.runs import UserError
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import bench as bench_command
from coding_study.entrypoints.shared import ExitCode
from tests.bench_fakes import ScriptedBenchProcess, optimal_user, power_law
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    make_environment,
    repository_root,
)

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
SIZES = "10,100,400,1600"
TIMING = re.compile(r"\d+(\.\d+)?(ms|µs|s)\b")


def environment_with(tmp_path, monkeypatch, process: ScriptedBenchProcess, prepare=None):
    toolchains = FakeToolchains(
        {Language.PYTHON: prepare or FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    root = repository_root(tmp_path, PRACTICE)
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    monkeypatch.setattr(bench_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


@pytest.fixture
def environment(tmp_path, monkeypatch):
    return environment_with(tmp_path, monkeypatch, optimal_user())


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["bench", "--sizes", SIZES, *arguments])


def lines(result) -> list[str]:
    return [TIMING.sub("T", line) for line in result.output.splitlines()]


def test_a_completed_bench_exits_0(environment):
    assert invoke().exit_code == ExitCode.SUCCESS


def test_the_report_shows_the_ladder_then_the_verdicts(environment):
    words = [" ".join(line.split()) for line in lines(invoke())]
    assert words == [
        "benching 3 targets at 4 sizes",
        "two-sum · python · sizes 10..1600 · reps 7 · power AC · load 0.5",
        "",
        "TARGET DECLARED n=10 n=1e2 n=4e2 n=1600 SLOPE BAND MEMORY",
        "brute-force O(n^2) T T T T 2.00 ~n^2 constant",
        "hash-map O(n) T T T T 1.00 ~n|nlogn linear",
        "you T T T T 1.00 ~n|nlogn linear",
        "",
        "verdict optimal: matches hash-map, 1.10x at n=1600 · confidence high "
        "(spread 0%, R^2 1.000)",
        "space linear, same as hash-map · confidence high",
    ]


def test_the_ladder_columns_line_up(environment):
    table = [line for line in invoke().output.splitlines() if line.startswith(("TARGET", "you"))]
    assert table[0].index("SLOPE") == table[1].index("1.00")


def test_a_second_bench_shows_the_history(environment):
    invoke()
    history = next(line for line in lines(invoke()) if line.startswith("history"))
    assert history.endswith("now same speed · 1st of 2 runs")


def test_output_never_shows_a_percentile(environment):
    assert "percentile" not in invoke().output


def test_a_suboptimal_user_is_reported(tmp_path, monkeypatch):
    process = optimal_user(user=power_law(2.0, output=[0, 1]))
    environment_with(tmp_path, monkeypatch, process)
    verdict = next(line for line in lines(invoke()) if line.startswith("verdict"))
    assert verdict.startswith("verdict   suboptimal: growth ~n^2 (slope 2.00), optimal is ~n|nlogn")


def test_a_wrong_answer_exits_1(tmp_path, monkeypatch):
    process = optimal_user(user=power_law(1.0, output=[7, 7]))
    environment_with(tmp_path, monkeypatch, process)
    result = invoke()
    assert result.exit_code == ExitCode.FAILURES
    assert "FAIL      wrong answer at n=10: expected [1, 0], got [7, 7]" in result.output


def test_user_code_that_does_not_load_exits_2(tmp_path, monkeypatch):
    error = UserError("ImportError", "no module named nope")
    environment_with(
        tmp_path, monkeypatch, ScriptedBenchProcess(load_errors={USER_TARGET_ID: error})
    )
    result = invoke()
    assert result.exit_code == ExitCode.USER_CODE_ERROR
    assert "ERROR     load: ImportError: no module named nope" in result.output


def test_user_code_that_does_not_build_exits_2(tmp_path, monkeypatch):
    failing = FakeLanguageRunner(BuildFailed(("Solution.java:3: error: ';' expected",)))
    environment_with(tmp_path, monkeypatch, optimal_user(), failing)
    result = invoke()
    assert (result.exit_code, "BUILD FAILED" in result.output) == (ExitCode.USER_CODE_ERROR, True)


def test_references_only_show_no_user_row_and_no_verdict(environment):
    output = lines(invoke("two-sum", "--refs-only"))
    assert [line for line in output if line.startswith(("you", "verdict"))] == []


@pytest.mark.parametrize("sizes", ["ten", "0,10", ""])
def test_bad_sizes_are_a_usage_error(environment, sizes):
    result = runner.invoke(cli.app, ["bench", "--sizes", sizes])
    assert result.exit_code == ExitCode.USAGE_ERROR


def test_without_an_attempt_bench_is_a_usage_error(tmp_path, monkeypatch):
    toolchains = FakeToolchains({Language.PYTHON: FakeLanguageRunner()})
    environment = make_environment(repository_root(tmp_path, PRACTICE), toolchains=toolchains)
    monkeypatch.setattr(bench_command, "load_environment", lambda *_: environment)
    assert invoke().exit_code == ExitCode.USAGE_ERROR


def test_a_solution_file_path_benches_its_problem_in_its_language(environment):
    path = environment.root / "python/practice/two_sum.py"
    assert "two-sum · python · sizes" in invoke(str(path)).output
