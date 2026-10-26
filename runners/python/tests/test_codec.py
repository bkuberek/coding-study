import math
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
