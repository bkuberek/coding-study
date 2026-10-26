import pytest

from cs_runner.dsl import (
    NodeKind,
    NodeType,
    Scalar,
    ScalarType,
    SequenceType,
    TypeSyntaxError,
    VoidType,
    parse_return_type,
    parse_value_type,
)

INT = ScalarType(Scalar.INT)


def test_parses_a_scalar():
    assert parse_value_type("double") == ScalarType(Scalar.DOUBLE)


def test_parses_a_node():
    assert parse_value_type("TreeNode") == NodeType(NodeKind.TREE_NODE)


def test_arrays_and_lists_share_one_representation():
    assert parse_value_type("int[]") == parse_value_type("list<int>") == SequenceType(INT)


def test_parses_a_matrix():
    assert parse_value_type("int[][]") == SequenceType(SequenceType(INT))


def test_parses_a_list_of_arrays():
    assert parse_value_type("list<int[]>") == SequenceType(SequenceType(INT))


def test_parses_the_deepest_list():
    expected = SequenceType(SequenceType(SequenceType(INT)))
    assert parse_value_type("list<list<list<int>>>") == expected


def test_parses_a_node_array():
    assert parse_value_type("ListNode[]") == SequenceType(NodeType(NodeKind.LIST_NODE))


def test_void_is_a_return_type():
    assert parse_return_type("void") == VoidType()


def test_return_types_include_value_types():
    assert parse_return_type("list<TreeNode>") == SequenceType(NodeType(NodeKind.TREE_NODE))


def test_void_is_not_a_value_type():
    with pytest.raises(TypeSyntaxError, match="void"):
        parse_value_type("void")


def test_rejects_an_unknown_type():
    with pytest.raises(TypeSyntaxError, match="map<int>"):
        parse_value_type("map<int>")
