from dataclasses import replace

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import OperationSequence
from coding_study.domain.concurrency import STALL_GRACE_MS, StressVariant, ThreadKind
from coding_study.domain.problem import Language, Problem
from coding_study.domain.stress import (
    ArithmeticSequence,
    Literal,
    Pick,
    RandomInteger,
    Repeat,
    Step,
    StressScenario,
    WorkerGroup,
)
from coding_study.domain.stress_runs import (
    StressSelection,
    expand_workers,
    plan_runs,
)
from tests.fakes import repository_root
from tests.helpers import CONCURRENCY_PROBLEMS

SETUP = OperationSequence(("Queue",), ((4,),))


@pytest.fixture(scope="module")
def queue(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("repository"), CONCURRENCY_PROBLEMS)
    return FsProblemRepository(root).load("bounded-blocking-queue")


def scenario(*groups: WorkerGroup) -> StressScenario:
    return StressScenario(setup=SETUP, workers=groups)


def group(*steps: Step, count: int = 2, repeat: int = 3, is_mix: bool = False) -> WorkerGroup:
    return WorkerGroup("producer", count, Repeat(repeat), steps, is_mix)


def test_sequence_template_strides_by_worker_and_iteration():
    steps = Step("put", (ArithmeticSequence(start=5, worker_stride=100, step=2),))
    workers = expand_workers(scenario(group(steps)), Language.PYTHON, seed=1)
    assert [worker.args for worker in workers] == [((5,), (7,), (9,)), ((105,), (107,), (109,))]


def test_literal_arguments_stay_as_written():
    workers = expand_workers(scenario(group(Step("put", (Literal(7),)))), Language.PYTHON, seed=1)
    assert workers[0].args == ((7,), (7,), (7,))


def test_every_iteration_runs_all_steps_in_order():
    steps = (Step("put", (Literal(1),)), Step("take", ()))
    workers = expand_workers(scenario(group(*steps, repeat=2)), Language.PYTHON, seed=1)
    assert workers[0].ops == ("put", "take", "put", "take")


def test_random_values_stay_within_their_range():
    steps = Step("put", (RandomInteger(3, 5),))
    workers = expand_workers(scenario(group(steps, repeat=200)), Language.PYTHON, seed=1)
    assert sorted({str(value) for (value,) in workers[0].args}) == ["3", "4", "5"]


def test_expansion_is_reproducible_for_a_seed():
    case = scenario(group(Step("put", (RandomInteger(0, 10**6),)), Step("take", (Pick((1, 2)),))))
    first = expand_workers(case, Language.PYTHON, seed=42)
    assert expand_workers(case, Language.PYTHON, seed=42) == first


def test_workers_draw_from_separate_streams():
    case = scenario(group(Step("put", (RandomInteger(0, 10**6),)), repeat=5))
    first, second = expand_workers(case, Language.PYTHON, seed=42)
    assert first.args != second.args


def test_a_mix_runs_one_weighted_step_per_iteration():
    mix = (Step("put", (Literal(1),), weight=1), Step("take", (), weight=1_000_000))
    workers = expand_workers(scenario(group(*mix, repeat=4, is_mix=True)), Language.PYTHON, 1)
    assert workers[0].ops == ("take", "take", "take", "take")


def test_repeat_can_differ_per_language():
    case = scenario(
        WorkerGroup("producer", 1, Repeat(4, {Language.PYTHON: 2}), (Step("take", ()),))
    )
    assert len(expand_workers(case, Language.PYTHON, 1)[0].ops) == 2


def test_default_repeat_applies_to_unlisted_languages():
    case = scenario(
        WorkerGroup("producer", 1, Repeat(4, {Language.PYTHON: 2}), (Step("take", ()),))
    )
    assert len(expand_workers(case, Language.JAVA, 1)[0].ops) == 4


def test_workers_are_ordered_by_group_then_index():
    case = scenario(
        WorkerGroup("producer", 2, Repeat(1), (Step("take", ()),)),
        WorkerGroup("consumer", 1, Repeat(1), (Step("take", ()),)),
    )
    labels = [worker.label for worker in expand_workers(case, Language.JAVA, 1)]
    assert labels == ["producer[0]", "producer[1]", "consumer[0]"]


def test_plan_runs_every_case_per_variant_and_run(queue):
    planned = plan_runs(queue, Language.JAVA, StressSelection())
    assert [run.run_id for run in planned[:4]] == [
        "s1:platform:0",
        "s1:platform:1",
        "s1:platform:2",
        "s1:virtual:0",
    ]


def test_plan_runs_cover_every_case_and_variant(queue):
    planned = plan_runs(queue, Language.JAVA, StressSelection())
    assert len(planned) == 2 * 2 * 3


def test_run_r_uses_seed_plus_r(queue):
    planned = plan_runs(queue, Language.PYTHON, StressSelection())
    assert [run.seed for run in planned[:3]] == [1000, 1001, 1002]


def test_a_base_seed_replaces_the_cases_seed(queue):
    planned = plan_runs(queue, Language.PYTHON, StressSelection(runs=2, seed=7))
    assert [run.seed for run in planned] == [7, 8, 7, 8]


def test_runs_override_the_problem_default(queue):
    planned = plan_runs(queue, Language.TYPESCRIPT, StressSelection(runs=10))
    assert len(planned) == 2 * 10


def test_python_threads_have_one_variant(queue):
    variants = {run.variant for run in plan_runs(queue, Language.PYTHON, StressSelection())}
    assert variants == {StressVariant.THREAD}


def test_jvm_runs_carry_their_thread_kind(queue):
    planned = plan_runs(queue, Language.KOTLIN, StressSelection(runs=1))
    assert [run.request.thread_kind for run in planned[:2]] == [
        ThreadKind.PLATFORM,
        ThreadKind.VIRTUAL,
    ]


def test_other_languages_send_no_thread_kind(queue):
    planned = plan_runs(queue, Language.TYPESCRIPT, StressSelection(runs=1))
    assert planned[0].request.thread_kind is None


def test_a_stress_runs_hang_guard_is_its_deadline_plus_the_grace(queue):
    planned = plan_runs(queue, Language.PYTHON, StressSelection(runs=1))
    assert planned[0].run_case().hang_guard_ms == 5000 + STALL_GRACE_MS


def test_python_repeat_override_reaches_the_request(queue):
    s2 = next(
        run for run in plan_runs(queue, Language.PYTHON, StressSelection()) if run.case.id == "s2"
    )
    assert len(s2.request.workers[0].ops) == 400


def test_problems_without_concurrency_plan_no_runs(queue):
    plain = replace(queue, meta=replace(queue.meta, concurrency=None))
    assert plan_runs(plain, Language.PYTHON, StressSelection()) == ()
