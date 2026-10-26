import pytest

from coding_study.domain.cases import Expected, FunctionInput, OperationSequence
from coding_study.domain.comparators import Mismatch, comparator_for
from coding_study.domain.problem import ComparatorSpec, ComparatorType
from coding_study.domain.runs import RunInput

NO_INPUT = FunctionInput({})
EXACT = comparator_for(ComparatorSpec(ComparatorType.EXACT))
UNORDERED = comparator_for(ComparatorSpec(ComparatorType.UNORDERED))
NESTED = comparator_for(ComparatorSpec(ComparatorType.UNORDERED_NESTED))
FLOAT = comparator_for(ComparatorSpec(ComparatorType.FLOAT))


def accepts(comparator, expected, actual, case_input: RunInput = NO_INPUT) -> bool:
    return comparator.compare(Expected(expected), actual, case_input) is None


# exact


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        (1, 1),
        (1, 1.0),
        ("a", "a"),
        (None, None),
        (True, True),
        ([1, [2, 3]], [1, [2, 3]]),
        ([], []),
        ({"a": [1]}, {"a": [1]}),
    ],
)
def test_exact_accepts_deeply_equal_values(expected, actual):
    assert accepts(EXACT, expected, actual)


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        (True, 1),
        (1, True),
        (False, 0),
        (0, None),
        ("1", 1),
        ([1, 2], [2, 1]),
        ([1], [1, 1]),
        ([[1]], [[1.5]]),
        ({"a": 1}, {"b": 1}),
        (1, 1.0000001),
    ],
)
def test_exact_rejects_different_values(expected, actual):
    assert not accepts(EXACT, expected, actual)


def test_exact_names_the_first_differing_index():
    mismatch = EXACT.compare(Expected([1, 2, 3]), [1, 5, 4], NO_INPUT)
    assert mismatch == Mismatch("first difference at index 1", first_difference=1)


def test_exact_reports_a_length_difference_after_a_common_prefix():
    mismatch = EXACT.compare(Expected([1, 2]), [1, 2, 3], NO_INPUT)
    assert mismatch == Mismatch("3 elements, expected 2", first_difference=2)


def test_exact_scalar_mismatch_needs_no_explanation():
    assert EXACT.compare(Expected(1), 2, NO_INPUT) == Mismatch()


def test_comparators_other_than_checker_require_an_expected_value():
    with pytest.raises(ValueError, match="expected value"):
        EXACT.compare(None, 1, NO_INPUT)


# unordered


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ([0, 3], [3, 0]),
        ([1, 1, 2], [1, 2, 1]),
        ([], []),
        ([[1, 2], [3]], [[3], [1, 2]]),
        ([1], [1.0]),
    ],
)
def test_unordered_accepts_equal_multisets(expected, actual):
    assert accepts(UNORDERED, expected, actual)


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ([0, 3], [3, 3]),
        ([1, 1, 2], [1, 2, 2]),
        ([1, 2], [1, 2, 3]),
        ([[1, 2]], [[2, 1]]),
        ([1], [True]),
        ([0, 3], None),
    ],
)
def test_unordered_rejects_different_multisets(expected, actual):
    assert not accepts(UNORDERED, expected, actual)


def test_unordered_explains_a_non_array_output():
    assert UNORDERED.compare(Expected([1]), 1, NO_INPUT) == Mismatch("expected an array")


# unordered-nested


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ([[1, 2], [3]], [[3], [2, 1]]),
        ([[-1, 0, 1], [-1, -1, 2]], [[2, -1, -1], [0, 1, -1]]),
        ([[]], [[]]),
        ([], []),
        (["ab", ["a"]], [["a"], "ab"]),
    ],
)
def test_unordered_nested_accepts_multisets_of_multisets(expected, actual):
    assert accepts(NESTED, expected, actual)


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ([[1, 2], [3]], [[1, 2], [3], [3]]),
        ([[1, 1]], [[1]]),
        ([[[1, 2]]], [[[2, 1]]]),
        ([[1]], [1]),
    ],
)
def test_unordered_nested_rejects_different_values(expected, actual):
    assert not accepts(NESTED, expected, actual)


# float


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        (1.0, 1.0000005),
        (1000.0, 1000.0009),
        ([0.5, [2.0]], [0.5000001, [2.0000001]]),
        (2, 2.0000001),
        ("x", "x"),
    ],
)
def test_float_accepts_values_within_tolerance(expected, actual):
    assert accepts(FLOAT, expected, actual)


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        (1.0, 1.00001),
        (1000.0, 1000.01),
        ([0.5], [0.5, 0.5]),
        (True, 1.0),
        (1.0, None),
    ],
)
def test_float_rejects_values_outside_tolerance(expected, actual):
    assert not accepts(FLOAT, expected, actual)


def test_float_tolerance_comes_from_the_spec():
    loose = comparator_for(ComparatorSpec(ComparatorType.FLOAT, tolerance=0.1))
    assert accepts(loose, 1.0, 1.09)


def test_float_tolerance_is_relative_above_one():
    assert accepts(FLOAT, 1e9, 1e9 + 900)


def test_float_names_the_first_differing_index():
    mismatch = FLOAT.compare(Expected([1.0, 2.0]), [1.0, 2.5], NO_INPUT)
    assert mismatch == Mismatch("first difference at index 1", first_difference=1)


# checker


def accept_even_sums(case_input, output, expected):
    return None if sum(output) % 2 == 0 else f"sum of {output} is odd"


CHECKER = comparator_for(ComparatorSpec(ComparatorType.CHECKER), accept_even_sums)


def test_checker_accepts_when_check_returns_none():
    assert CHECKER.compare(None, [1, 3], NO_INPUT) is None


def test_checker_reports_the_reason_from_check():
    assert CHECKER.compare(None, [1, 2], NO_INPUT) == Mismatch("sum of [1, 2] is odd")


def test_checker_receives_function_arguments_output_and_expected():
    received = []
    comparator = comparator_for(
        ComparatorSpec(ComparatorType.CHECKER), lambda *arguments: received.append(arguments)
    )
    comparator.compare(Expected([0, 1]), [1, 0], FunctionInput({"nums": [2, 7]}))
    assert received == [({"nums": [2, 7]}, [1, 0], [0, 1])]


def test_checker_receives_none_when_the_case_has_no_expected_value():
    received = []
    comparator = comparator_for(
        ComparatorSpec(ComparatorType.CHECKER), lambda *arguments: received.append(arguments)
    )
    comparator.compare(None, 1, NO_INPUT)
    assert received[0][2] is None


def test_checker_receives_operation_sequences_as_ops_and_args():
    received = []
    comparator = comparator_for(
        ComparatorSpec(ComparatorType.CHECKER), lambda *arguments: received.append(arguments)
    )
    comparator.compare(None, [None], OperationSequence(("Box",), ((1,),)))
    assert received[0][0] == {"ops": ["Box"], "args": [[1]]}


def test_checker_that_raises_rejects_the_output():
    def broken(case_input, output, expected):
        raise KeyError("nums")

    comparator = comparator_for(ComparatorSpec(ComparatorType.CHECKER), broken)
    assert comparator.compare(None, 1, NO_INPUT) == Mismatch("checker raised KeyError: 'nums'")


def test_checker_comparator_requires_a_checker():
    with pytest.raises(ValueError, match="checker"):
        comparator_for(ComparatorSpec(ComparatorType.CHECKER))


# ops

LRU_OPS = OperationSequence(("LRUCache", "put", "get", "keys"), ((2,), (1, 1), (1,), ()))
OPS = comparator_for(ComparatorSpec(ComparatorType.OPS))


def test_ops_accepts_equal_outputs_per_operation():
    assert accepts(OPS, [None, None, 1, [1]], [None, None, 1, [1]], LRU_OPS)


def test_ops_reports_the_first_failing_operation():
    mismatch = OPS.compare(Expected([None, None, 1, [1]]), [None, None, -1, [1]], LRU_OPS)
    assert mismatch == Mismatch("op 2 get: expected 1, got -1", first_difference=2)


def test_ops_reports_a_different_number_of_outputs():
    mismatch = OPS.compare(Expected([None, None, 1, [1]]), [None, None], LRU_OPS)
    assert mismatch == Mismatch("2 outputs for 4 operations")


def test_ops_rejects_a_non_array_output():
    assert OPS.compare(Expected([None]), None, LRU_OPS) == Mismatch("expected an array")


def test_ops_per_method_comparator_overrides_exact():
    spec = ComparatorSpec(ComparatorType.OPS, per_method={"keys": ComparatorType.UNORDERED})
    comparator = comparator_for(spec)
    ops = OperationSequence(("Box", "keys"), ((), ()))
    assert accepts(comparator, [None, [1, 2]], [None, [2, 1]], ops)


def test_ops_per_method_float_uses_the_spec_tolerance():
    spec = ComparatorSpec(
        ComparatorType.OPS, tolerance=0.1, per_method={"mean": ComparatorType.FLOAT}
    )
    ops = OperationSequence(("Stats", "mean"), ((), ()))
    assert accepts(comparator_for(spec), [None, 1.0], [None, 1.05], ops)


def test_ops_other_methods_stay_exact():
    spec = ComparatorSpec(ComparatorType.OPS, per_method={"keys": ComparatorType.UNORDERED})
    ops = OperationSequence(("Box", "get"), ((), ()))
    assert not accepts(comparator_for(spec), [None, [1, 2]], [None, [2, 1]], ops)


def test_ops_requires_an_operation_sequence():
    with pytest.raises(ValueError, match="operation sequence"):
        OPS.compare(Expected([None]), [None], NO_INPUT)


@pytest.mark.parametrize(
    ("comparator_type", "label"),
    [
        (ComparatorType.EXACT, None),
        (ComparatorType.UNORDERED, "unordered"),
        (ComparatorType.UNORDERED_NESTED, "unordered-nested"),
        (ComparatorType.FLOAT, "float, tolerance 1e-06"),
        (ComparatorType.OPS, None),
    ],
)
def test_comparators_describe_themselves_for_failure_reports(comparator_type, label):
    assert comparator_for(ComparatorSpec(comparator_type)).label == label
