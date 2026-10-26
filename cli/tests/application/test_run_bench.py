from pathlib import Path

import pytest

from coding_study.application.ports import BenchCode, BuildFailed
from coding_study.application.run_bench import (
    BenchOptions,
    BenchResult,
    RunBenchRequest,
    run_bench,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.bench_records import MachineState, PowerSource
from coding_study.domain.bench_runs import USER_TARGET_ID, Warmup
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.errors import ContentError, UsageError
from coding_study.domain.problem import Language
from coding_study.domain.runs import Raised, UserError
from tests.bench_fakes import BENCH_SIZES, ScriptedBenchProcess, optimal_user, power_law
from tests.fakes import (
    FakeLanguageRunner,
    FakeMachine,
    FakeStubGenerator,
    FakeToolchains,
    make_environment,
)
from tests.fakes import repository_root as copy_repository
from tests.helpers import CONCURRENCY_PROBLEMS

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
OPTIONS = BenchOptions(sizes=BENCH_SIZES)
BUSY = MachineState("Test CPU", PowerSource.BATTERY, 0.5, 8)


@pytest.fixture
def runner() -> FakeLanguageRunner:
    return FakeLanguageRunner()


def environment_with(
    tmp_path: Path, runner: FakeLanguageRunner, process: ScriptedBenchProcess, **parts: object
):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains({Language.PYTHON: runner}, {Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(root, toolchains=toolchains, runner_process=process, **parts)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


def bench(environment, **fields) -> BenchResult:
    fields.setdefault("options", OPTIONS)
    return run_bench(environment, RunBenchRequest(**fields), lambda _line: None)


@pytest.fixture
def process() -> ScriptedBenchProcess:
    return optimal_user()


@pytest.fixture
def environment(tmp_path, runner, process):
    return environment_with(tmp_path, runner, process)


def sent_job(process: ScriptedBenchProcess):
    return process.requests[-1].job


def test_concurrent_problems_have_no_bench(tmp_path, runner):
    root = copy_repository(tmp_path, CONCURRENCY_PROBLEMS)
    toolchains = FakeToolchains({Language.PYTHON: runner}, {Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(root, toolchains=toolchains, runner_process=optimal_user())
    start_attempt(environment, StartRequest("bounded-blocking-queue"))
    with pytest.raises(UsageError, match="bench is not available for concurrent problems"):
        bench(environment)


def test_the_user_and_every_reference_run_in_one_bench(environment, process):
    bench(environment)
    assert [t.target_id for t in sent_job(process).targets] == [
        USER_TARGET_ID,
        "brute-force",
        "hash-map",
    ]


def test_the_user_and_the_expected_source_report_outputs(environment, process):
    bench(environment)
    outputs = [t.target_id for t in sent_job(process).targets if t.emits_output]
    assert outputs == [USER_TARGET_ID, "hash-map"]


def test_one_input_per_size_ascending(environment, process):
    bench(environment, options=BenchOptions(sizes=(400, 10, 100, 10)))
    assert [i.size for i in sent_job(process).inputs] == [10, 100, 400]


def test_sizes_default_to_the_size_ladder(environment, process):
    bench(environment, options=BenchOptions())
    assert [i.size for i in sent_job(process).inputs] == [10, 100]


def test_inputs_are_the_same_in_every_run(environment, process):
    bench(environment)
    bench(environment)
    first, second = process.requests
    assert first.job.inputs == second.job.inputs


def test_the_batch_cap_counts_the_elements_of_each_input(environment, process):
    bench(environment, options=BenchOptions(sizes=(10,)))
    (bench_input,) = sent_job(process).inputs
    assert bench_input.max_batch == 10**6 // 11


def test_inputs_differ_between_sizes(environment, process):
    bench(environment)
    small, large = sent_job(process).inputs[:2]
    assert small.input != large.input


def test_python_warms_up_with_its_check_call_only(environment, process):
    bench(environment)
    assert sent_job(process).settings.warmup == Warmup(1, 1, 0.05)


def test_reps_default_to_the_config(environment, process):
    bench(environment)
    assert sent_job(process).settings.reps == 7


def test_reps_can_be_overridden(environment, process):
    bench(environment, options=BenchOptions(sizes=BENCH_SIZES, reps=3))
    assert sent_job(process).settings.reps == 3


def test_memory_can_be_turned_off(environment, process):
    bench(environment, options=BenchOptions(sizes=BENCH_SIZES, memory=False))
    assert not sent_job(process).settings.memory


def test_the_hang_guard_covers_the_budget(environment, process):
    bench(environment)
    assert sent_job(process).hang_guard_ms == 10_000


def test_the_bench_prepares_user_code_and_references_together(environment, runner):
    bench(environment)
    scope = runner.scopes[-1]
    assert isinstance(scope, BenchCode)
    assert ([s.approach_id for s in scope.sources], scope.references_only) == (
        ["brute-force", "hash-map"],
        False,
    )


def test_a_linear_user_matches_the_optimal_reference(environment):
    verdict = bench(environment).verdict
    assert verdict is not None
    assert (verdict.time.verdict, verdict.time.reference_id) == (Verdict.OPTIMAL, "hash-map")


def test_a_quadratic_user_is_suboptimal(tmp_path, runner):
    process = optimal_user(user=power_law(2.0, output=[0, 1]))
    verdict = bench(environment_with(tmp_path, runner, process)).verdict
    assert verdict is not None
    assert verdict.time.verdict is Verdict.SUBOPTIMAL


def test_the_run_is_stored_with_its_attempt(environment):
    result = bench(environment)
    assert result.attempt is not None
    assert environment.progress.bench_history("two-sum", Language.PYTHON)


def test_the_first_run_has_no_history(environment):
    assert bench(environment).history is None


def test_a_second_run_compares_with_the_first(environment):
    bench(environment)
    history = bench(environment).history
    assert history is not None
    assert (history.size, history.runs) == (1600, 2)


def test_a_wrong_output_is_a_wrong_answer_at_its_size(tmp_path, runner):
    process = optimal_user(user=power_law(1.0, output=[5, 5]))
    wrong = bench(environment_with(tmp_path, runner, process)).wrong_answer
    assert wrong is not None
    assert (wrong.size, wrong.detail) == (10, "expected [1, 0], got [5, 5]")


def test_a_wrong_answer_is_not_judged(tmp_path, runner):
    process = optimal_user(user=power_law(1.0, output=[5, 5]))
    assert bench(environment_with(tmp_path, runner, process)).verdict is None


def test_a_wrong_answer_is_stored_as_unknown(tmp_path, runner):
    process = optimal_user(user=power_law(1.0, output=[5, 5]))
    environment = environment_with(tmp_path, runner, process)
    bench(environment)
    assert len(environment.progress.bench_history("two-sum", Language.PYTHON)) == 1


def raises_at(size: int):
    linear = power_law(1.0, output=[0, 1])

    def measure(target, bench_input):
        measured = linear(target, bench_input)
        if bench_input.size != size:
            return measured
        failure = Raised(UserError("IndexError", "list index out of range"), 5)
        return type(measured)(bench_input.size, failure=failure)

    return measure


def test_an_exception_on_a_bench_input_is_a_wrong_answer(tmp_path, runner):
    process = optimal_user(user=raises_at(100))
    wrong = bench(environment_with(tmp_path, runner, process)).wrong_answer
    assert wrong is not None
    assert (wrong.size, wrong.detail) == (100, "IndexError: list index out of range")


def test_user_code_that_does_not_load_is_reported(tmp_path, runner):
    error = UserError("ImportError", "bad import")
    process = ScriptedBenchProcess(load_errors={USER_TARGET_ID: error})
    result = bench(environment_with(tmp_path, runner, process))
    assert result.load_error == error


def test_user_code_that_does_not_load_is_not_stored(tmp_path, runner):
    process = ScriptedBenchProcess(load_errors={USER_TARGET_ID: UserError("ImportError", "x")})
    environment = environment_with(tmp_path, runner, process)
    bench(environment)
    assert environment.progress.bench_history("two-sum", Language.PYTHON) == ()


def test_a_build_failure_is_reported(tmp_path, process):
    failed = BuildFailed(("Solution.java:3: error",))
    result = bench(environment_with(tmp_path, FakeLanguageRunner(failed), process))
    assert result.build_failure == failed


def test_references_only_run_without_the_user(environment, process):
    bench(environment, slug="two-sum", references_only=True)
    assert USER_TARGET_ID not in [t.target_id for t in sent_job(process).targets]


def test_references_only_have_no_attempt(environment):
    assert bench(environment, slug="two-sum", references_only=True).attempt is None


def test_references_only_prepare_only_the_references(environment, runner):
    bench(environment, slug="two-sum", references_only=True)
    scope = runner.scopes[-1]
    assert isinstance(scope, BenchCode)
    assert scope.references_only


def test_a_reference_that_does_not_load_is_a_warning(tmp_path, runner):
    process = optimal_user()
    process.load_errors = {"brute-force": UserError("SyntaxError", "invalid syntax")}
    result = bench(environment_with(tmp_path, runner, process))
    assert "reference brute-force did not load: SyntaxError: invalid syntax" in result.warnings


def test_a_busy_machine_caps_confidence(tmp_path, runner, process):
    environment = environment_with(tmp_path, runner, process, machine=FakeMachine(BUSY))
    verdict = bench(environment).verdict
    assert verdict is not None
    assert verdict.time.confidence is Confidence.MEDIUM


def test_a_busy_machine_is_a_warning(tmp_path, runner, process):
    environment = environment_with(tmp_path, runner, process, machine=FakeMachine(BUSY))
    assert "on battery power: confidence capped at medium" in bench(environment).warnings


def test_without_an_attempt_the_bench_is_a_usage_error(tmp_path, runner, process):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains({Language.PYTHON: runner}, {Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    with pytest.raises(UsageError):
        bench(environment)


def test_a_problem_without_a_generator_is_a_content_error(environment):
    (environment.root / "problems" / "0001-two-sum" / "generator.py").unlink()
    with pytest.raises(ContentError, match=r"generator\.py"):
        bench(environment)
