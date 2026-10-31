"""`cstudy test --perf`: after a full pass, a short bench and its verdict line."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.application.ports import CaseListener, RunnerLaunch
from coding_study.application.run_bench import PERF_REPS
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.bench_runs import USER_TARGET_ID, BenchReport, BenchRequest
from coding_study.domain.problem import Language
from coding_study.domain.runs import Returned, RunCase, RunJob, RunReport, RunRequest
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.bench_fakes import ScriptedBenchProcess, optimal_user, power_law
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
    two_sum,
)
from tests.helpers import SCHEMAS_DIRECTORY

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
EVENTS_VALIDATOR = Draft202012Validator(
    json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
)


def wrong(job: RunJob, case: RunCase) -> Returned:
    return Returned([9, 9], 1000)


@dataclass
class CasesAndBench:
    """Answers test cases with `cases` and benches with `bench_process`."""

    cases: ScriptedRunnerProcess
    bench_process: ScriptedBenchProcess = field(default_factory=optimal_user)

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        return self.cases.run(launch, request, listener)

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        return self.bench_process.bench(launch, request)


def environment_with(tmp_path, monkeypatch, process: CasesAndBench):
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    root = repository_root(tmp_path, PRACTICE)
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


@pytest.fixture
def process() -> CasesAndBench:
    return CasesAndBench(ScriptedRunnerProcess(two_sum))


@pytest.fixture
def environment(tmp_path, monkeypatch, process):
    return environment_with(tmp_path, monkeypatch, process)


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["test", *arguments])


def verdict_lines(result) -> list[str]:
    return [line for line in result.output.splitlines() if line.startswith(("verdict", "FAIL "))]


def test_a_full_pass_prints_one_verdict_line(environment):
    assert len(verdict_lines(invoke("--perf"))) == 1


def test_the_verdict_line_names_its_confidence(environment):
    """The fixture's ladder has two sizes, too few to judge: `unknown`, confidence low."""
    line = verdict_lines(invoke("--perf"))[0]
    assert line.startswith("verdict   unknown: not enough data")
    assert "confidence low" in line


def test_the_short_bench_runs_three_reps(environment, process):
    invoke("--perf")
    assert process.bench_process.requests[-1].job.settings.reps == PERF_REPS


def test_the_short_bench_is_stored(environment):
    invoke("--perf")
    assert len(environment.progress.bench_history("two-sum", Language.PYTHON)) == 1


def test_a_full_pass_with_any_verdict_exits_0(tmp_path, monkeypatch):
    bench = optimal_user(user=power_law(2.0, output=[0, 1]))
    environment_with(tmp_path, monkeypatch, CasesAndBench(ScriptedRunnerProcess(two_sum), bench))
    assert invoke("--perf").exit_code == ExitCode.SUCCESS


def test_a_failing_run_skips_the_bench(tmp_path, monkeypatch):
    process = CasesAndBench(ScriptedRunnerProcess(wrong))
    environment_with(tmp_path, monkeypatch, process)
    invoke("--perf")
    assert process.bench_process.requests == []


def test_a_subset_of_cases_skips_the_bench(environment, process):
    invoke("--perf", "--case", "ex1")
    assert process.bench_process.requests == []


def test_without_perf_there_is_no_bench(environment, process):
    invoke()
    assert process.bench_process.requests == []


def test_a_wrong_answer_on_a_bench_input_exits_1(tmp_path, monkeypatch):
    bench = optimal_user(**{USER_TARGET_ID: power_law(1.0, output=[7, 7])})
    environment_with(tmp_path, monkeypatch, CasesAndBench(ScriptedRunnerProcess(two_sum), bench))
    result = invoke("--perf")
    assert result.exit_code == ExitCode.FAILURES
    assert verdict_lines(result)[0].startswith("FAIL      wrong answer at n=10")


def perf_document(*arguments: str) -> dict:
    return json.loads(invoke("--json", "--perf", *arguments).stdout)


def test_json_perf_holds_the_verdict(environment):
    perf = perf_document()["perf"]
    assert (perf["verdict"], perf["confidence"], perf["wrong_answer"]) == ("unknown", "low", None)


def test_json_perf_holds_the_verdict_line(environment):
    assert perf_document()["perf"]["text"].startswith("verdict   unknown: not enough data")


def test_json_perf_is_null_when_a_case_fails(tmp_path, monkeypatch):
    environment_with(tmp_path, monkeypatch, CasesAndBench(ScriptedRunnerProcess(wrong)))
    assert perf_document()["perf"] is None


def test_json_perf_names_a_wrong_answer_without_a_verdict(tmp_path, monkeypatch):
    bench = optimal_user(**{USER_TARGET_ID: power_law(1.0, output=[7, 7])})
    environment_with(tmp_path, monkeypatch, CasesAndBench(ScriptedRunnerProcess(two_sum), bench))
    perf = perf_document()["perf"]
    assert (perf["verdict"], perf["wrong_answer"][:30]) == (None, "FAIL      wrong answer at n=10")


def test_json_perf_exits_as_the_bench_says(tmp_path, monkeypatch):
    bench = optimal_user(**{USER_TARGET_ID: power_law(1.0, output=[7, 7])})
    environment_with(tmp_path, monkeypatch, CasesAndBench(ScriptedRunnerProcess(two_sum), bench))
    found = invoke("--json", "--perf")
    assert (found.exit_code, json.loads(found.stdout)["exit_code"]) == (1, 1)


def events(*arguments: str) -> list[dict]:
    return [
        json.loads(line) for line in invoke("--events", "--perf", *arguments).stdout.splitlines()
    ]


def test_the_perf_result_follows_a_full_pass(environment):
    assert [event["type"] for event in events()][-2:] == ["perf_result", "run_end"]


def test_the_perf_result_is_the_json_documents_perf(environment):
    found = events()
    perf_result = next(event for event in found if event["type"] == "perf_result")
    assert perf_result == {"type": "perf_result", "version": 1} | found[-1]["summary"]["perf"]


def test_a_failing_run_writes_no_perf_result(tmp_path, monkeypatch):
    environment_with(tmp_path, monkeypatch, CasesAndBench(ScriptedRunnerProcess(wrong)))
    assert "perf_result" not in [event["type"] for event in events()]


def test_every_perf_event_matches_the_schema(environment):
    invalid = [event for event in events() if not EVENTS_VALIDATOR.is_valid(event)]
    assert invalid == []
