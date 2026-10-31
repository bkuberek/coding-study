"""`cstudy verify --ladder`: the references' measured bands against their declared `time_class`."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import pytest

from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import CaseListener, RunnerLaunch
from coding_study.application.verify_content import SkippedCheck, VerifyRequest, verify_content
from coding_study.application.verify_ladder import SETTLE_SECONDS
from coding_study.domain.bench_records import MachineState, PowerSource
from coding_study.domain.bench_runs import USER_TARGET_ID, BenchReport, BenchRequest
from coding_study.domain.bench_verdict import LadderStatus
from coding_study.domain.problem import Language
from coding_study.domain.runs import RunReport, RunRequest, UserError
from tests.bench_fakes import ScriptedBenchProcess, optimal_user, power_law, timed
from tests.e2e import e2e_environment
from tests.fakes import QUIET_MACHINE, FakeMachine, repository_root

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
TWO_SUM = "problems/0001-two-sum"
BUSY_MACHINE = MachineState("Test CPU", PowerSource.AC, 6.0, 8)


class Benches(Protocol):
    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport: ...


@dataclass
class RealCasesScriptedBench:
    """Runs test cases for real (mini Python runner); benches are scripted."""

    cases: SubprocessRunner
    benches: Benches

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        return self.cases.run(launch, request)

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        return self.benches.bench(launch, request)


@dataclass
class BenchesPerAttempt:
    """Each bench request is measured by the next of `attempts`; the last one keeps answering."""

    attempts: tuple[ScriptedBenchProcess, ...]
    requests: list[BenchRequest] = field(default_factory=list[BenchRequest])

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        self.requests.append(request)
        attempt = self.attempts[min(len(self.requests), len(self.attempts)) - 1]
        return attempt.bench(launch, request)


def environment_with(tmp_path: Path, benches: Benches, machine: FakeMachine | None = None):
    root = repository_root(tmp_path, PRACTICE)
    meta = root / TWO_SUM / "meta.yaml"
    meta.write_text(meta.read_text().replace("[10, 100]", "[10, 100, 400, 1600]"))
    process = RealCasesScriptedBench(SubprocessRunner(root / ".cs" / "runs"), benches)
    return e2e_environment(root, runner_process=process, machine=machine or FakeMachine())


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


# Machine load: a busy machine is a warning, and a contradiction there is measured once more


CONTRADICTING = {"hash-map": power_law(2.0)}


def contradicting_then_consistent() -> BenchesPerAttempt:
    return BenchesPerAttempt((optimal_user(**CONTRADICTING), optimal_user()))


def settling() -> FakeMachine:
    return FakeMachine(BUSY_MACHINE, settled_state=QUIET_MACHINE)


def test_a_ladder_records_the_machine_it_ran_on(environment):
    assert verify(environment, ladder=True).ladder[0].machine == QUIET_MACHINE


def test_a_ladder_on_a_quiet_machine_has_no_load_note(environment):
    assert verify(environment, ladder=True).ladder[0].notes == ()


def test_a_ladder_on_a_busy_machine_is_a_warning(tmp_path):
    environment = environment_with(tmp_path, optimal_user(), FakeMachine(BUSY_MACHINE))
    assert verify(environment, ladder=True).ladder[0].notes == (
        "measured on a busy machine (load 6.0 is above half of 8 cores): timings drift, "
        "so verify again when it is idle",
    )


def test_a_consistent_ladder_on_a_busy_machine_is_measured_once(tmp_path):
    benches = optimal_user()
    verify(environment_with(tmp_path, benches, FakeMachine(BUSY_MACHINE)), ladder=True)
    assert len(benches.requests) == 1


def test_a_contradiction_on_a_quiet_machine_is_measured_once(tmp_path):
    benches = contradicting_then_consistent()
    problem = verify(environment_with(tmp_path, benches), ladder=True)
    assert (problem.passed, len(benches.requests)) == (False, 1)


def test_a_contradiction_on_a_busy_machine_is_measured_again(tmp_path):
    benches = contradicting_then_consistent()
    verify(environment_with(tmp_path, benches, settling()), ladder=True)
    assert len(benches.requests) == 2


def test_the_second_measurement_decides(tmp_path):
    environment = environment_with(tmp_path, contradicting_then_consistent(), settling())
    assert verify(environment, ladder=True).passed


def test_the_ladder_waits_for_the_machine_to_settle_before_measuring_again(tmp_path):
    machine = settling()
    verify(environment_with(tmp_path, contradicting_then_consistent(), machine), ladder=True)
    assert machine.settles == [SETTLE_SECONDS]


def test_a_measured_again_ladder_names_the_first_machine(tmp_path):
    environment = environment_with(tmp_path, contradicting_then_consistent(), settling())
    (result,) = verify(environment, ladder=True).ladder
    assert (result.retried_after, result.machine) == (BUSY_MACHINE, QUIET_MACHINE)


def test_a_measured_again_ladder_says_so(tmp_path):
    environment = environment_with(tmp_path, contradicting_then_consistent(), settling())
    assert verify(environment, ladder=True).ladder[0].notes == (
        "contradicted its class on a busy machine (load 6.0 is above half of 8 cores); "
        "measured again after waiting up to 60s for it to settle",
    )


def test_a_ladder_is_measured_again_once_at_most(tmp_path):
    benches = BenchesPerAttempt((optimal_user(**CONTRADICTING),))
    problem = verify(environment_with(tmp_path, benches, FakeMachine(BUSY_MACHINE)), ladder=True)
    assert (problem.passed, len(benches.requests)) == (False, 2)


def test_a_reference_that_does_not_load_is_not_measured_again(tmp_path):
    benches = optimal_user(**CONTRADICTING)
    benches.load_errors = {"brute-force": UserError("ImportError", "broken")}
    verify(environment_with(tmp_path, benches, FakeMachine(BUSY_MACHINE)), ladder=True)
    assert len(benches.requests) == 1


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
