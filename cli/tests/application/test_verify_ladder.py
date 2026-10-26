"""`cstudy verify --ladder`: the references' measured bands against their declared `time_class`."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.application.verify_content import SkippedCheck, VerifyRequest, verify_content
from coding_study.domain.bench_runs import USER_TARGET_ID, BenchReport, BenchRequest
from coding_study.domain.bench_verdict import LadderStatus
from coding_study.domain.problem import Language
from coding_study.domain.runs import RunReport, RunRequest, UserError
from tests.bench_fakes import ScriptedBenchProcess, optimal_user, power_law, timed
from tests.e2e import e2e_environment
from tests.fakes import repository_root

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
TWO_SUM = "problems/0001-two-sum"


@dataclass
class RealCasesScriptedBench:
    """Runs test cases for real (mini Python runner); benches are scripted."""

    cases: SubprocessRunner
    benches: ScriptedBenchProcess

    def run(self, launch: RunnerLaunch, request: RunRequest) -> RunReport:
        return self.cases.run(launch, request)

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        return self.benches.bench(launch, request)


def environment_with(tmp_path: Path, benches: ScriptedBenchProcess):
    root = repository_root(tmp_path, PRACTICE)
    meta = root / TWO_SUM / "meta.yaml"
    meta.write_text(meta.read_text().replace("[10, 100]", "[10, 100, 400, 1600]"))
    process = RealCasesScriptedBench(SubprocessRunner(root / ".cs" / "runs"), benches)
    return e2e_environment(root, runner_process=process)


def verify(environment, **fields):
    request = VerifyRequest(slugs=("two-sum",), language=Language.PYTHON, **fields)
    return verify_content(environment, request, lambda _line: None).problems[0]


@pytest.fixture
def benches() -> ScriptedBenchProcess:
    return optimal_user()


@pytest.fixture
def environment(tmp_path, benches):
    return environment_with(tmp_path, benches)


def test_references_in_their_declared_bands_pass(environment):
    assert verify(environment, ladder=True).passed


def test_every_reference_is_checked(environment):
    (result,) = verify(environment, ladder=True).ladder
    statuses = [(check.approach_id, check.status) for check in result.checks]
    assert statuses == [
        ("brute-force", LadderStatus.CONSISTENT),
        ("hash-map", LadderStatus.CONSISTENT),
    ]


def test_a_band_contradicting_the_declared_class_fails(tmp_path):
    benches = optimal_user(**{"hash-map": power_law(2.0)})
    problem = verify(environment_with(tmp_path, benches), ladder=True)
    assert not problem.passed
    assert [c.message for c in problem.ladder[0].contradictions] == [
        "hash-map declares O(n) but measures ~n^2 (slope 2.00); "
        "time / n varies 160x, more than the 4x tolerance"
    ]


def fixed_cost_then_linear():
    return optimal_user(**{"hash-map": timed(lambda size: 1000.0 + 10.0 * size, [1, 0])})


def test_a_band_explained_by_a_fixed_cost_passes(tmp_path):
    assert verify(environment_with(tmp_path, fixed_cost_then_linear()), ladder=True).passed


def test_a_band_explained_by_a_fixed_cost_is_reported_as_tolerated(tmp_path):
    problem = verify(environment_with(tmp_path, fixed_cost_then_linear()), ladder=True)
    assert [c.approach_id for c in problem.ladder[0].tolerated] == ["hash-map"]


def test_too_few_sizes_are_reported_but_do_not_fail(tmp_path):
    def two_sizes_then_budget(target, bench_input):
        measured = power_law(2.0)(target, bench_input)
        if bench_input.size < 400:
            return measured
        return type(measured)(bench_input.size, exceeded_ns=5 * 10**9)

    benches = optimal_user(**{"brute-force": two_sizes_then_budget})
    problem = verify(environment_with(tmp_path, benches), ladder=True)
    assert problem.passed
    assert [c.status for c in problem.ladder[0].unclassified] == [LadderStatus.UNCLASSIFIED]


def test_a_reference_that_does_not_load_in_the_bench_fails(tmp_path):
    benches = optimal_user()
    benches.load_errors = {"hash-map": UserError("ImportError", "broken")}
    problem = verify(environment_with(tmp_path, benches), ladder=True)
    assert problem.ladder[0].problems == ("hash-map does not load: ImportError: broken",)


def test_the_ladder_benches_references_only(environment, benches):
    verify(environment, ladder=True)
    targets = [target.target_id for target in benches.requests[-1].job.targets]
    assert USER_TARGET_ID not in targets


def test_the_ladder_skips_memory(environment, benches):
    verify(environment, ladder=True)
    assert not benches.requests[-1].job.settings.memory


def test_without_ladder_nothing_is_benched(environment, benches):
    verify(environment)
    assert benches.requests == []


def test_references_that_fail_their_cases_are_not_benched(environment, benches):
    solution = environment.root / TWO_SUM / "solutions" / "hash-map.py"
    solution.write_text(solution.read_text().replace("return [", "return [0, 0] or ["))
    verify(environment, ladder=True)
    assert benches.requests == []


def without_generator(environment):
    request = VerifyRequest(slugs=("lru-cache",), language=Language.PYTHON, ladder=True)
    return verify_content(environment, request, lambda _line: None).problems[0]


def test_the_ladder_does_not_apply_without_a_generator(environment):
    assert without_generator(environment).skipped == (SkippedCheck.LADDER,)


def test_a_problem_without_a_generator_passes_the_ladder_request(environment):
    assert without_generator(environment).passed


def test_a_problem_without_a_generator_is_not_benched(environment, benches):
    without_generator(environment)
    assert benches.requests == []
