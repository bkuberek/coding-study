"""Concurrent problems through the schemas and the document mapping."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.concurrency import (
    BrokenReference,
    ConcurrencyModel,
    PythonGranularity,
    ThreadKind,
)
from coding_study.domain.errors import ContentError
from coding_study.domain.problem import Language, Problem
from coding_study.domain.stress import (
    ArithmeticSequence,
    EqualMultisets,
    Pick,
    RandomInteger,
    Repeat,
    Selector,
    StressScenario,
)
from tests.fakes import repository_root
from tests.helpers import CONCURRENCY_PROBLEMS

DIRECTORY = "problems/0001-bounded-blocking-queue"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return repository_root(tmp_path, CONCURRENCY_PROBLEMS)


def load(root: Path) -> Problem:
    return FsProblemRepository(root).load("bounded-blocking-queue")


def edit_meta(root: Path, change) -> None:
    path = root / DIRECTORY / "meta.yaml"
    document = yaml.safe_load(path.read_text())
    change(document)
    path.write_text(yaml.safe_dump(document))


def edit_stress(root: Path, change, case_id: str = "s1") -> None:
    path = root / DIRECTORY / "tests.json"
    document = json.loads(path.read_text())
    case = next(case for case in document["cases"] if case["id"] == case_id)
    change(case)
    path.write_text(json.dumps(document))


def load_errors(root: Path) -> str:
    with pytest.raises(ContentError) as raised:
        load(root)
    return "\n".join(str(issue) for issue in raised.value.issues)


def scenario(problem: Problem, case_id: str = "s1") -> StressScenario:
    stress = next(case.input for case in problem.cases if case.id == case_id)
    assert isinstance(stress, StressScenario)
    return stress


def test_concurrency_models_are_per_language(root):
    models = load(root).meta.concurrency.models  # type: ignore[union-attr]
    assert (models[Language.PYTHON], models[Language.TYPESCRIPT]) == (
        ConcurrencyModel.THREADS,
        ConcurrencyModel.ASYNC,
    )


def test_one_model_string_applies_to_every_language(root):
    def threads_only(meta: dict[str, Any]) -> None:
        meta["languages"] = ["java", "python"]
        meta["concurrency"]["model"] = "threads"

    edit_meta(root, threads_only)
    models = load(root).meta.concurrency.models  # type: ignore[union-attr]
    assert set(models.values()) == {ConcurrencyModel.THREADS}


def test_go_and_rust_take_a_model_and_a_repeat_of_their_own(root):
    def go_and_rust(meta: dict[str, Any]) -> None:
        meta["languages"] = [*meta["languages"], "go", "rust"]
        meta["concurrency"]["model"].update(go="threads", rust="threads")

    def repeats(case: dict[str, Any]) -> None:
        case["stress"]["workers"][0]["repeat"] = {"default": 500, "go": 300, "rust": 200}

    edit_meta(root, go_and_rust)
    edit_stress(root, repeats)
    problem = load(root)
    models = problem.meta.concurrency.models  # type: ignore[union-attr]
    repeat = scenario(problem).workers[0].repeat
    assert (models[Language.GO], models[Language.RUST]) == (ConcurrencyModel.THREADS,) * 2
    assert repeat == Repeat(500, {Language.GO: 300, Language.RUST: 200})


def test_jvm_threads_are_read(root):
    concurrency = load(root).meta.concurrency
    assert concurrency.jvm_threads == (ThreadKind.PLATFORM, ThreadKind.VIRTUAL)  # type: ignore[union-attr]


def test_perturbation_defaults_apply(root):
    perturb = load(root).meta.concurrency.perturb  # type: ignore[union-attr]
    assert (perturb.yield_probability, perturb.max_yields, perturb.python_granularity) == (
        0.05,
        3,
        PythonGranularity.LINE,
    )


def test_broken_references_are_read(root):
    broken = load(root).meta.concurrency.broken[0]  # type: ignore[union-attr]
    assert broken == BrokenReference(
        "no-lock",
        "Deque without a lock",
        "Spin-waits on the size, then mutates a shared deque with no mutual exclusion",
        ("s1",),
        (Language.JAVA, Language.KOTLIN, Language.PYTHON),
    )


def test_blocking_methods_are_marked(root):
    methods = load(root).meta.signature.methods  # type: ignore[union-attr]
    assert [method.blocking for method in methods] == [True, True, False]


def test_concurrent_approaches_have_no_complexity_classes(root):
    approach = load(root).meta.approaches[0]
    assert (approach.time_class, approach.space_class) == (None, None)


def test_stress_cases_keep_their_templates(root):
    producer = scenario(load(root)).workers[0]
    assert producer.steps[0].args == (ArithmeticSequence(0, 1_000_000, 1),)


def test_stress_cases_keep_the_document_for_the_checker(root):
    assert scenario(load(root)).document["seed"] == 1000


def test_stress_invariants_are_read(root):
    invariants = scenario(load(root)).invariants
    assert invariants[0] == EqualMultisets(Selector("put", "arg0"), Selector("take"))


def test_rand_and_pick_templates_are_read(root):
    def templates(case: dict[str, Any]) -> None:
        case["stress"]["workers"][0]["steps"][0]["args"] = [{"$rand": [1, 9]}]
        case["stress"]["workers"][1]["steps"] = [{"op": "put", "args": [{"$pick": [3, 5]}]}]

    edit_stress(root, templates)
    workers = scenario(load(root)).workers
    assert (workers[0].steps[0].args, workers[1].steps[0].args) == (
        (RandomInteger(1, 9),),
        (Pick((3, 5)),),
    )


def test_a_mix_is_read_with_weights(root):
    def mix(case: dict[str, Any]) -> None:
        group = case["stress"]["workers"][0]
        del group["steps"]
        group["mix"] = [
            {"op": "size", "args": [], "weight": 3},
            {"op": "take", "args": [], "weight": 1},
        ]

    edit_stress(root, mix)
    group = scenario(load(root)).workers[0]
    assert (group.is_mix, [step.weight for step in group.steps]) == (True, [3, 1])


def test_a_stress_case_may_not_have_expected(root):
    edit_stress(root, lambda case: case.update(expected=[1]))
    assert "tests.json" in load_errors(root)


def test_a_stress_case_needs_invariants_or_final_expected(root):
    def neither(case: dict[str, Any]) -> None:
        del case["stress"]["invariants"]
        del case["stress"]["final"]["expected"]

    edit_stress(root, neither)
    assert "tests.json" in load_errors(root)


def test_unknown_templates_are_rejected(root):
    def unknown(case: dict[str, Any]) -> None:
        case["stress"]["workers"][0]["steps"][0]["args"] = [{"$range": [1, 2]}]

    edit_stress(root, unknown)
    assert "tests.json" in load_errors(root)


def test_concurrent_problems_need_a_concurrency_block(root):
    edit_meta(root, lambda meta: meta.pop("concurrency"))
    assert "concurrency" in load_errors(root)


def test_other_kinds_may_not_have_a_concurrency_block(root):
    edit_meta(root, lambda meta: meta.update(kind="design"))
    assert "meta.yaml" in load_errors(root)


def test_concurrent_approaches_may_not_declare_classes(root):
    def classes(meta: dict[str, Any]) -> None:
        meta["approaches"][0].update(time_class="1", space_class="n")

    edit_meta(root, classes)
    assert "meta.yaml" in load_errors(root)


def test_blocking_is_rejected_outside_concurrent_problems(root):
    def design(meta: dict[str, Any]) -> None:
        meta.update(kind="design", track="lld")
        del meta["concurrency"]
        for approach in meta["approaches"]:
            approach.update(time_class="1", space_class="n")

    edit_meta(root, design)
    edit_stress(root, lambda case: case.clear() or case.update(copy.deepcopy(_SEQUENTIAL)), "s1")
    edit_stress(root, lambda case: case.clear() or case.update(copy.deepcopy(_SEQUENTIAL_2)), "s2")
    assert "only allowed in concurrent problems" in load_errors(root)


_SEQUENTIAL = {"id": "s1", "ops": ["BoundedBlockingQueue"], "args": [[1]], "expected": [None]}
_SEQUENTIAL_2 = {"id": "s2", "ops": ["BoundedBlockingQueue"], "args": [[1]], "expected": [None]}
