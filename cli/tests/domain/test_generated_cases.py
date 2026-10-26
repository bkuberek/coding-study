from dataclasses import replace

import pytest

from coding_study.domain.cases import (
    Case,
    Expected,
    FunctionInput,
    GeneratedInput,
    OperationSequence,
)
from coding_study.domain.generated_cases import (
    ORACLE_MAX_SIZE,
    GeneratedCase,
    expected_source,
    generated_run_input,
    materialized_case,
    oracle_approach,
    oracle_inputs,
)
from coding_study.domain.judging import RunnableCase
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    ContentStatus,
    Difficulty,
    Perf,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.signature import FunctionSignature, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType


def approach(approach_id: str, role: ApproachRole, *, oracle: bool = False) -> Approach:
    linear = ComplexityClass.LINEAR
    return Approach(approach_id, approach_id, role, "O(n)", "O(n)", linear, linear, oracle)


META = ProblemMeta(
    id="0001",
    slug="two-sum",
    title="Two Sum",
    status=ContentStatus.READY,
    difficulty=Difficulty.EASY,
    track=Track.DSA,
    kind=ProblemKind.FUNCTION,
    signature=FunctionSignature("twoSum", (), Returns(ScalarType(Scalar.INT))),
    comparator=ComparatorSpec(ComparatorType.EXACT),
    approaches=(
        approach("brute-force", ApproachRole.BRUTE, oracle=True),
        approach("sorting", ApproachRole.OPTIMAL),
        approach("hash-map", ApproachRole.OPTIMAL),
    ),
)


def test_function_kind_documents_are_arguments():
    assert generated_run_input(ProblemKind.FUNCTION, {"nums": [1]}) == FunctionInput({"nums": [1]})


def test_class_kind_documents_are_operation_sequences():
    document = {"ops": ["LRUCache", "get"], "args": [[2], [1]]}
    assert generated_run_input(ProblemKind.DESIGN, document) == OperationSequence(
        ("LRUCache", "get"), ((2,), (1,))
    )


@pytest.mark.parametrize(
    "document",
    [
        {"ops": ["LRUCache"]},
        {"ops": "LRUCache", "args": [[2]]},
        {"ops": ["LRUCache"], "args": [2]},
        {"ops": ["LRUCache", "get"], "args": [[2]]},
        {"ops": [1], "args": [[2]]},
    ],
)
def test_malformed_operation_sequences_are_rejected(document):
    with pytest.raises(ValueError, match="ops"):
        generated_run_input(ProblemKind.DESIGN, document)


def test_oracle_inputs_use_seeds_from_one():
    assert [oracle.seed for oracle in oracle_inputs(3)] == [1, 2, 3]


def test_oracle_inputs_have_distinct_case_ids():
    assert len({oracle.case_id for oracle in oracle_inputs(200)}) == 200


def test_oracle_sizes_stay_small():
    assert all(1 <= oracle.n <= ORACLE_MAX_SIZE for oracle in oracle_inputs(200))


def test_oracle_sizes_vary():
    assert len({oracle.n for oracle in oracle_inputs(200)}) > 10


def test_oracle_inputs_are_deterministic():
    assert oracle_inputs(50) == oracle_inputs(50)


def test_oracle_inputs_can_start_at_another_seed():
    assert [oracle.case_id for oracle in oracle_inputs(2, first_seed=7)] == [
        "oracle-7",
        "oracle-8",
    ]


def test_an_oracle_input_depends_only_on_its_seed():
    assert oracle_inputs(1, first_seed=17)[0] == oracle_inputs(20)[16]


def test_expected_source_is_the_declared_approach():
    meta = replace(META, perf=Perf(expected_from="sorting"))
    assert expected_source(meta, {"brute-force", "sorting", "hash-map"}) == "sorting"


def test_expected_source_defaults_to_the_first_optimal_approach_with_python():
    assert expected_source(META, {"brute-force", "hash-map"}) == "hash-map"


def test_no_expected_source_without_an_optimal_python_approach():
    assert expected_source(META, {"brute-force"}) is None


def test_oracle_approach_is_the_one_marked_oracle():
    assert oracle_approach(META) == "brute-force"


def test_no_oracle_approach():
    unmarked = replace(META, approaches=(approach("hash-map", ApproachRole.OPTIMAL),))
    assert oracle_approach(unmarked) is None


def test_materialized_case_keeps_id_hang_guard_and_note():
    case = Case("g1", GeneratedInput(100, 1), hang_guard_ms=500, note="large")
    generated = GeneratedCase(FunctionInput({"nums": [1]}), Expected(0))
    assert materialized_case(case, generated) == RunnableCase(
        "g1",
        FunctionInput({"nums": [1]}),
        Expected(0),
        generated=True,
        hang_guard_ms=500,
        note="large",
    )
