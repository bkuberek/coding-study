import pytest

from coding_study.adapters.problem_documents import cases_from_document, meta_from_document
from coding_study.domain.cases import (
    Case,
    Expected,
    FunctionInput,
    GeneratedInput,
    OperationSequence,
)
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.problem import (
    ALL_LANGUAGES,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    Language,
    LeetCodeReference,
    ProblemKind,
    StubSource,
)
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Returns,
)
from coding_study.domain.time_limits import FactorTimeLimit
from coding_study.domain.type_dsl import (
    ArrayType,
    NodeKind,
    NodeType,
    Scalar,
    ScalarType,
    VoidType,
)
from tests.helpers import load_fixture_meta, load_fixture_tests

META_SOURCE = "problems/0001-two-sum/meta.yaml"
TESTS_SOURCE = "problems/0001-two-sum/tests.json"
INT = ScalarType(Scalar.INT)
TREE = NodeType(NodeKind.TREE_NODE)
UNORDERED = ComparatorSpec(ComparatorType.UNORDERED)


def two_sum_meta():
    return meta_from_document(load_fixture_meta("0001-two-sum"), META_SOURCE)


def lru_cache_meta():
    return meta_from_document(load_fixture_meta("0002-lru-cache"), META_SOURCE)


def test_maps_function_signature_with_parsed_types():
    assert two_sum_meta().signature == FunctionSignature(
        name="twoSum",
        params=(Param("nums", ArrayType(INT)), Param("target", INT)),
        returns=Returns(ArrayType(INT)),
    )


def test_maps_class_signature():
    assert lru_cache_meta().signature == ClassSignature(
        name="LRUCache",
        constructor_params=(Param("capacity", INT),),
        methods=(
            Method("get", (Param("key", INT),), Returns(INT)),
            Method("put", (Param("key", INT), Param("value", INT)), Returns(VoidType())),
        ),
    )


def test_maps_identity_and_classification():
    meta = two_sum_meta()
    assert (meta.id, meta.slug, meta.title, meta.kind, meta.patterns) == (
        "0001",
        "two-sum",
        "Two Sum",
        ProblemKind.FUNCTION,
        ("arrays-hashing",),
    )


def test_maps_comparator():
    assert two_sum_meta().comparator == UNORDERED


def test_maps_approaches_in_ladder_order():
    approaches = two_sum_meta().approaches
    assert [(a.id, a.role, a.time_class, a.oracle) for a in approaches] == [
        ("brute-force", ApproachRole.BRUTE, ComplexityClass.QUADRATIC, True),
        ("hash-map", ApproachRole.OPTIMAL, ComplexityClass.LINEAR, False),
    ]


def test_maps_perf_block():
    perf = two_sum_meta().perf
    assert (perf.size_ladder, perf.expected_from, perf.time_limit) == (
        (100, 1000, 10000, 100000),
        "hash-map",
        FactorTimeLimit(5),
    )


def test_maps_references_and_related():
    meta = two_sum_meta()
    assert (meta.references.leetcode, meta.related, meta.estimate_minutes) == (
        LeetCodeReference(1, "https://leetcode.com/problems/two-sum/"),
        ("three-sum",),
        15,
    )


def test_applies_spec_defaults_for_omitted_fields():
    meta = two_sum_meta()
    assert (meta.languages, meta.stub, meta.levels, meta.order, meta.hang_guard_ms) == (
        ALL_LANGUAGES,
        StubSource.GENERATED,
        (),
        1000,
        None,
    )


def test_listed_languages_keep_their_document_order():
    document = load_fixture_meta("0001-two-sum")
    document["languages"] = ["rust", "python", "typescript", "java", "kotlin", "go"]
    assert meta_from_document(document, META_SOURCE).languages == (
        Language.RUST,
        Language.PYTHON,
        Language.TYPESCRIPT,
        Language.JAVA,
        Language.KOTLIN,
        Language.GO,
    )


def test_perf_defaults_apply_without_perf_block():
    meta = load_fixture_meta("0001-two-sum")
    del meta["perf"]
    perf = meta_from_document(meta, META_SOURCE).perf
    assert (perf.size_ladder, perf.budget_ms, perf.time_limit) == (
        (100, 1000, 10000, 100000),
        2000,
        None,
    )


def test_maps_return_and_param_modifiers():
    meta = load_fixture_meta("0001-two-sum")
    meta["signature"]["function"] = {
        "name": "lowestCommonAncestor",
        "params": [
            {"name": "root", "type": "TreeNode"},
            {"name": "p", "type": "TreeNode", "ref_of": "root"},
        ],
        "returns": {"type": "TreeNode", "as": "index", "of": "root", "no_alias_with": "root"},
    }
    assert meta_from_document(meta, META_SOURCE).signature == FunctionSignature(
        name="lowestCommonAncestor",
        params=(Param("root", TREE), Param("p", TREE, ref_of="root")),
        returns=Returns(
            TREE, serialize_as=NodeSerialization.INDEX, index_of="root", no_alias_with="root"
        ),
    )


def test_modifiers_naming_unknown_params_are_content_errors():
    meta = load_fixture_meta("0001-two-sum")
    meta["signature"]["function"] = {
        "name": "copyList",
        "params": [{"name": "head", "type": "ListNode"}],
        "returns": {"type": "ListNode", "no_alias_with": "original"},
    }
    with pytest.raises(ContentError) as raised:
        meta_from_document(meta, META_SOURCE)
    assert raised.value.issues == (
        ContentIssue(
            META_SOURCE,
            "signature.function.returns.no_alias_with",
            'no parameter named "original"',
        ),
    )


def test_every_modifier_issue_is_reported():
    meta = load_fixture_meta("0002-lru-cache")
    meta["signature"]["class"]["methods"][0]["returns"]["output_from"] = "missing"
    meta["signature"]["class"]["constructor"]["params"][0]["ref_of"] = "missing"
    with pytest.raises(ContentError) as raised:
        meta_from_document(meta, META_SOURCE)
    assert len(raised.value.issues) == 2


def test_maps_float_tolerance_and_per_method_comparators():
    meta = load_fixture_meta("0002-lru-cache")
    meta["comparator"] = {"type": "ops", "tolerance": 1e-5, "per_method": {"get": "unordered"}}
    assert meta_from_document(meta, META_SOURCE).comparator == ComparatorSpec(
        ComparatorType.OPS, 1e-5, {"get": ComparatorType.UNORDERED}
    )


def test_invalid_type_is_reported_at_its_field():
    meta = load_fixture_meta("0001-two-sum")
    meta["signature"]["function"]["params"][1]["type"] = "list<int"
    with pytest.raises(ContentError) as raised:
        meta_from_document(meta, META_SOURCE)
    assert raised.value.issues == (
        ContentIssue(
            META_SOURCE,
            "signature.function.params[1].type",
            'invalid type "list<int": expected ">" at column 9',
        ),
    )


def test_void_param_is_rejected():
    meta = load_fixture_meta("0002-lru-cache")
    meta["signature"]["class"]["methods"][0]["params"][0]["type"] = "void"
    with pytest.raises(ContentError, match=r"signature\.class\.methods\[0\]\.params\[0\]\.type"):
        meta_from_document(meta, META_SOURCE)


def test_invalid_return_type_is_reported_at_its_field():
    meta = load_fixture_meta("0001-two-sum")
    meta["signature"]["function"]["returns"]["type"] = "ints"
    with pytest.raises(ContentError, match=r"signature\.function\.returns\.type"):
        meta_from_document(meta, META_SOURCE)


def test_duplicate_approach_ids_are_rejected():
    meta = load_fixture_meta("0001-two-sum")
    meta["approaches"][1]["id"] = "brute-force"
    with pytest.raises(ContentError, match='duplicate approach id "brute-force"'):
        meta_from_document(meta, META_SOURCE)


def two_sum_cases():
    return cases_from_document(load_fixture_tests("0001-two-sum"), UNORDERED, TESTS_SOURCE)


def test_maps_function_case():
    assert two_sum_cases()[0] == Case(
        id="ex1",
        input=FunctionInput({"nums": [4, 9, 2, 8], "target": 11}),
        expected=Expected([1, 2]),
        visible=True,
    )


def test_maps_case_note():
    assert two_sum_cases()[2].note == "negatives and zero"


def test_maps_generated_case_without_expected():
    assert two_sum_cases()[3] == Case(id="g1", input=GeneratedInput(n=100000, seed=1))


def test_maps_operation_sequence_and_null_expected_values():
    [case] = cases_from_document(
        load_fixture_tests("0002-lru-cache"), ComparatorSpec(ComparatorType.OPS), TESTS_SOURCE
    )
    assert (case.input, case.expected) == (
        OperationSequence(
            ops=("LRUCache", "put", "put", "get", "put", "get", "get"),
            args=((2,), (1, 1), (2, 2), (1,), (3, 3), (2,), (3,)),
        ),
        Expected([None, None, None, 1, None, -1, 3]),
    )


def test_case_without_expected_is_rejected_for_non_checker_comparators():
    tests = load_fixture_tests("0001-two-sum")
    del tests["cases"][1]["expected"]
    with pytest.raises(ContentError, match=r"cases\[1\]: missing expected"):
        cases_from_document(tests, UNORDERED, TESTS_SOURCE)


def test_checker_problems_may_omit_expected():
    tests = load_fixture_tests("0001-two-sum")
    del tests["cases"][1]["expected"]
    cases = cases_from_document(tests, ComparatorSpec(ComparatorType.CHECKER), TESTS_SOURCE)
    assert cases[1].expected is None


def test_duplicate_case_ids_are_rejected():
    tests = load_fixture_tests("0001-two-sum")
    tests["cases"][2]["id"] = "ex1"
    with pytest.raises(ContentError, match='duplicate case id "ex1"'):
        cases_from_document(tests, UNORDERED, TESTS_SOURCE)
