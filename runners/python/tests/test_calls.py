from typing import Any

import pytest

from cs_runner.calls import BoundCall, bind
from cs_runner.dsl import parse_return_type, parse_value_type
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.request import Member, NodeSerialization, Param, Returns
from cs_support import ListNode


def param(name: str, type_text: str, ref_of: str | None = None) -> Param:
    return Param(name, parse_value_type(type_text), ref_of)


def member(params: tuple[Param, ...], returns: Returns) -> Member:
    return Member("call", "call", params, returns)


def arguments(call: BoundCall) -> list[Any]:
    return call.arguments


TWO_SUM = member(
    (param("nums", "int[]"), param("target", "int")), Returns(parse_return_type("int[]"))
)
PICK_NODE = member(
    (param("head", "ListNode"), param("node", "ListNode", ref_of="head")),
    Returns(parse_return_type("ListNode"), serialize_as=NodeSerialization.INDEX, index_of="head"),
)
PICK_TREE_NODE = member(
    (param("root", "TreeNode"), param("node", "TreeNode", ref_of="root")),
    Returns(parse_return_type("TreeNode"), serialize_as=NodeSerialization.VALUE),
)
SORT_VALUES = member(
    (param("values", "int[]"),), Returns(parse_return_type("void"), output_from="values")
)
NOOP = member((param("value", "int"),), Returns(parse_return_type("void")))
COPY_LIST = member(
    (param("head", "ListNode"),), Returns(parse_return_type("ListNode"), no_alias_with="head")
)


def test_arguments_follow_the_declared_parameter_order():
    call = bind(TWO_SUM, {"target": 9, "nums": [2, 7]})
    assert call.arguments == [[2, 7], 9]


def test_a_missing_input_is_a_case_input_error():
    with pytest.raises(CaseInputError, match="target"):
        bind(TWO_SUM, {"nums": [2, 7]})


def test_an_ordinary_return_is_encoded_with_its_type():
    assert bind(TWO_SUM, {"nums": [], "target": 0}).encode_result([0, 1]) == [0, 1]


def test_ref_of_passes_the_first_node_with_that_value():
    head, node = arguments(bind(PICK_NODE, {"head": [5, 6, 7], "node": 7}))
    assert node is head.next.next


def test_ref_of_resolves_tree_nodes_in_level_order():
    root, node = arguments(
        bind(PICK_TREE_NODE, {"root": [3, 9, 20, None, None, 15, 7], "node": 15})
    )
    assert node is root.right.left


def test_ref_of_null_passes_none():
    assert bind(PICK_NODE, {"head": [5], "node": None}).arguments[1] is None


def test_ref_of_a_missing_value_is_a_case_input_error():
    with pytest.raises(CaseInputError, match="no node with value 9"):
        bind(PICK_NODE, {"head": [5, 6], "node": 9})


def test_as_index_encodes_the_position_in_the_parameter():
    call = bind(PICK_NODE, {"head": [5, 6, 7], "node": 6})
    assert call.encode_result(call.arguments[1]) == 1


def test_as_index_encodes_null_as_minus_one():
    assert bind(PICK_NODE, {"head": [5], "node": 5}).encode_result(None) == -1


def test_as_index_of_a_node_outside_the_parameter_is_invalid():
    call = bind(PICK_NODE, {"head": [5], "node": 5})
    with pytest.raises(InvalidOutputError, match="head"):
        call.encode_result(ListNode(5))


def test_as_value_encodes_the_node_value():
    call = bind(PICK_TREE_NODE, {"root": [3, 9], "node": 9})
    assert call.encode_result(call.arguments[1]) == 9


def test_as_value_encodes_null_as_null():
    assert bind(PICK_TREE_NODE, {"root": [3], "node": 3}).encode_result(None) is None


def test_output_from_encodes_the_parameter_after_the_call():
    call = bind(SORT_VALUES, {"values": [3, 1, 2]})
    arguments(call)[0].sort()
    assert call.encode_result(None) == [1, 2, 3]


def test_a_void_return_encodes_as_null():
    assert bind(NOOP, {"value": 1}).encode_result("ignored") is None


def test_no_alias_with_accepts_new_nodes():
    assert bind(COPY_LIST, {"head": [1, 2]}).encode_result(ListNode(1, ListNode(2))) == [1, 2]


def test_no_alias_with_rejects_returning_the_input():
    call = bind(COPY_LIST, {"head": [1, 2]})
    with pytest.raises(InvalidOutputError, match="head"):
        call.encode_result(call.arguments[0])


def test_no_alias_with_rejects_new_nodes_that_reach_the_input():
    call = bind(COPY_LIST, {"head": [1, 2]})
    original = arguments(call)[0]
    with pytest.raises(InvalidOutputError):
        call.encode_result(ListNode(1, original.next))


def test_no_alias_with_accepts_null():
    assert bind(COPY_LIST, {"head": []}).encode_result(None) == []
