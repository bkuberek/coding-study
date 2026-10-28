import math
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from cs_runner.codec import decode, encode
from cs_runner.dsl import parse_value_type
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_support import GraphNode, ListNode, TreeNode

ROUND_TRIPS = [
    ("int", 0),
    ("int", -2147483648),
    ("int", 2147483647),
    ("long", -9007199254740991),
    ("double", 0.1),
    ("double", 1.7976931348623157e308),
    ("bool", True),
    ("bool", False),
    ("string", ""),
    ("string", 'üñí "quoted" \\ line\nbreak\ttab'),
    ("char", "€"),
    ("int[]", []),
    ("int[]", [1, -2, 3]),
    ("long[]", [9007199254740991, -1]),
    ("double[]", [0.5, -1.25]),
    ("bool[]", [True, False]),
    ("char[]", ["a", "€"]),
    ("string[]", ["x", ""]),
    ("int[][]", [[1, 2], [], [3]]),
    ("double[][]", [[0.5], [1.5, 2.5]]),
    ("char[][]", [["a"], ["b", "c"]]),
    ("decimal", "0"),
    ("decimal", "2500"),
    ("decimal", "-0.5"),
    ("decimal", "1234.0625"),
    ("decimal", "0.0000000000000000000000000001"),
    ("decimal", "9999999999999999999999999999.5"),
    ("decimal[]", ["1", "2.5", "-3"]),
    ("decimal[][]", [["1"], [], ["0.01"]]),
    ("list<decimal>", ["0.01"]),
    ("date", "2024-02-29"),
    ("date", "0001-01-01"),
    ("date", "9999-12-31"),
    ("date[]", ["2024-01-01", "2023-12-31"]),
    ("date[][]", [["2024-01-01"], []]),
    ("list<date>", ["2024-03-01"]),
    ("string[][]", [["x"], ["y", "z"]]),
    ("list<int>", [1, 2]),
    ("list<string>", ["a", "b"]),
    ("list<int[]>", [[1, 2], []]),
    ("list<list<int>>", [[1], [2, 3], []]),
    ("list<list<list<int>>>", [[[1], []], []]),
    ("ListNode", []),
    ("ListNode", [1, 2, 3]),
    ("TreeNode", []),
    ("TreeNode", [3, 9, 20, None, None, 15, 7]),
    ("TreeNode", [1, None, 2]),
    ("GraphNode", []),
    ("GraphNode", [[]]),
    ("GraphNode", [[2, 4], [1, 3], [2, 4], [1, 3]]),
    ("ListNode[]", [[1, 2], [], [3]]),
    ("list<TreeNode>", [[1, None, 2], []]),
]


def encoded(value: object, type_text: str) -> object:
    return encode(value, parse_value_type(type_text))


def decoded(value: Any, type_text: str) -> Any:
    return decode(value, parse_value_type(type_text))


@pytest.mark.parametrize(("type_text", "value"), ROUND_TRIPS, ids=lambda item: str(item))
def test_decoding_then_encoding_returns_the_input(type_text, value):
    assert encoded(decoded(value, type_text), type_text) == value


def test_an_integral_double_input_becomes_a_float():
    assert isinstance(decoded(3, "double"), float)


def test_an_integer_double_output_is_written_as_a_float():
    assert isinstance(encoded(3, "double"), float)


def test_a_tuple_output_is_accepted_as_a_list():
    assert encoded((1, 2), "int[]") == [1, 2]


def test_decimal_input_keeps_its_scale():
    value = decoded("2500.00", "decimal")
    assert (value, value.as_tuple().exponent) == (Decimal("2500"), -2)


def test_decimal_input_is_a_decimal():
    assert isinstance(decoded("2500.00", "decimal"), Decimal)


def test_date_input_is_a_date():
    assert decoded("2024-02-29", "date") == date(2024, 2, 29)


def test_decimal_inputs_inside_a_list_are_decimals():
    assert decoded(["1.50", "2"], "list<decimal>") == [Decimal("1.5"), Decimal(2)]


@pytest.mark.parametrize(
    ("value", "canonical"),
    [
        (Decimal("2500.00"), "2500"),
        (Decimal("2500.50"), "2500.5"),
        (Decimal("10.10"), "10.1"),
        (Decimal("100"), "100"),
        (Decimal("0.00"), "0"),
        (Decimal("-0"), "0"),
        (Decimal("-0.0"), "0"),
        (Decimal("1E+3"), "1000"),
        (Decimal("0E+3"), "0"),
        (Decimal("1E-7"), "0.0000001"),
        (Decimal("-1.50E+1"), "-15"),
    ],
)
def test_a_decimal_output_is_written_in_canonical_form(value, canonical):
    assert encoded(value, "decimal") == canonical


def test_a_decimal_output_beyond_the_context_precision_stays_exact():
    exact = "123456789012345678901234567890.123456789"
    assert encoded(Decimal(exact), "decimal") == exact


def test_decoding_then_encoding_a_non_canonical_decimal_gives_the_canonical_text():
    assert encoded(decoded("2500.00", "decimal"), "decimal") == "2500"
    assert encoded(decoded("-0.0", "decimal"), "decimal") == "0"


@pytest.mark.parametrize(
    ("value", "type_text"),
    [
        (2500, "decimal"),
        (2500.5, "decimal"),
        (True, "decimal"),
        (None, "decimal"),
        ("007", "decimal"),
        ("1e3", "decimal"),
        (".5", "decimal"),
        ("5.", "decimal"),
        ("+5", "decimal"),
        (" 5", "decimal"),
        ("NaN", "decimal"),
        ("Infinity", "decimal"),
        ("\uff11\uff12", "decimal"),
        ("1.5", "date"),
        (20240101, "date"),
        ("20240101", "date"),
        ("2024-1-1", "date"),
        ("2024-01-01T00:00:00", "date"),
        ("2023-02-29", "date"),
        ("0000-01-01", "date"),
        ("\uff12\uff10\uff12\uff14-01-01", "date"),
        ("5", "decimal[]"),
        ([5], "decimal[]"),
    ],
)
def test_a_decimal_or_date_input_of_the_wrong_shape_is_a_case_input_error(value, type_text):
    with pytest.raises(CaseInputError):
        decoded(value, type_text)


@pytest.mark.parametrize(
    ("value", "type_text"),
    [
        (1.5, "decimal"),
        (5, "decimal"),
        (True, "decimal"),
        (None, "decimal"),
        ("5", "decimal"),
        (date(2024, 1, 1), "decimal"),
        (Decimal("NaN"), "decimal"),
        (Decimal("sNaN"), "decimal"),
        (Decimal("Infinity"), "decimal"),
        (Decimal("-Infinity"), "decimal"),
        ("2024-01-01", "date"),
        (20240101, "date"),
        (None, "date"),
        (Decimal("1"), "date"),
        (datetime(2024, 1, 1), "date"),
        (datetime(2024, 1, 1, 12, 30), "date"),
    ],
)
def test_a_value_that_is_not_a_decimal_or_date_is_invalid_output(value, type_text):
    with pytest.raises(InvalidOutputError):
        encoded(value, type_text)


def test_a_float_decimal_output_names_the_python_type():
    with pytest.raises(InvalidOutputError, match=r"\[1\]: expected decimal, got float"):
        encoded([Decimal(1), 2.5], "list<decimal>")


def test_a_non_finite_decimal_output_is_named():
    with pytest.raises(InvalidOutputError, match="non-finite decimal: NaN"):
        encoded(Decimal("NaN"), "decimal")


def test_a_datetime_output_is_not_a_date():
    with pytest.raises(InvalidOutputError, match="expected date, got datetime"):
        encoded(datetime(2024, 1, 1), "date")


def test_list_input_builds_list_nodes():
    head = decoded([1, 2], "ListNode")
    assert isinstance(head, ListNode)
    assert (head.val, head.next and head.next.val) == (1, 2)


def test_cyclic_list_input_links_the_tail_to_cycle_at():
    head = decoded({"values": [3, 2, 0, -4], "cycle_at": 1}, "ListNode")
    second = head.next
    tail = second.next.next
    assert tail.next is second


def test_tree_input_fills_children_in_level_order():
    root = decoded([3, 9, 20, None, None, 15, 7], "TreeNode")
    assert root.right.left.val == 15


def test_tree_input_with_a_null_root_is_none():
    assert decoded([None], "TreeNode") is None


def test_graph_input_links_neighbors_by_value():
    node = decoded([[2, 4], [1, 3], [2, 4], [1, 3]], "GraphNode")
    assert isinstance(node, GraphNode)
    assert [neighbor.val for neighbor in node.neighbors] == [2, 4]


@pytest.mark.parametrize(
    ("value", "type_text"),
    [
        ("1", "int"),
        (True, "int"),
        (1, "string"),
        ("ab", "char"),
        (5, "int[]"),
        ([[9]], "GraphNode"),
    ],
)
def test_input_of_the_wrong_shape_is_a_case_input_error(value, type_text):
    with pytest.raises(CaseInputError):
        decoded(value, type_text)


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
def test_a_non_finite_double_is_invalid_output(value):
    with pytest.raises(InvalidOutputError, match="non-finite"):
        encoded(value, "double")


@pytest.mark.parametrize(
    ("value", "type_text"),
    [
        (1.0, "int"),
        (True, "int"),
        (2**31, "int"),
        (2**53, "long"),
        (1, "bool"),
        (None, "string"),
        ("", "char"),
        ("ab", "char"),
        ({1, 2}, "int[]"),
        ("abc", "char[]"),
    ],
)
def test_a_value_that_does_not_fit_the_type_is_invalid_output(value, type_text):
    with pytest.raises(InvalidOutputError):
        encoded(value, type_text)


def test_invalid_output_names_where_the_bad_value_is():
    with pytest.raises(InvalidOutputError, match=r"\[1\]: expected int, got str"):
        encoded([1, "2"], "int[]")


def test_a_cyclic_list_output_is_invalid():
    head = decoded({"values": [1, 2], "cycle_at": 0}, "ListNode")
    with pytest.raises(InvalidOutputError, match="list too long or cyclic"):
        encoded(head, "ListNode")


def test_a_tree_output_that_reuses_a_node_is_invalid():
    leaf = TreeNode(2)
    with pytest.raises(InvalidOutputError, match="cycle or a shared node"):
        encoded(TreeNode(1, leaf, leaf), "TreeNode")


def test_a_graph_output_needs_values_one_to_k():
    first, third = GraphNode(1), GraphNode(3)
    first.neighbors.append(third)
    third.neighbors.append(first)
    with pytest.raises(InvalidOutputError, match=r"1\.\.k"):
        encoded(first, "GraphNode")


def test_node_outputs_are_duck_typed():
    node = SimpleNamespace(val=7, next=None)
    assert encoded(node, "ListNode") == [7]


def test_a_node_output_without_its_link_field_is_invalid():
    with pytest.raises(InvalidOutputError, match="next"):
        encoded(SimpleNamespace(val=7), "ListNode")


def test_a_node_value_must_be_an_int():
    with pytest.raises(InvalidOutputError, match="node value"):
        encoded(SimpleNamespace(val="x", next=None), "ListNode")
