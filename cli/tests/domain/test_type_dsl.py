import pytest

from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeKind,
    NodeType,
    Scalar,
    ScalarType,
    TypeSyntaxError,
    VoidType,
    parse_return_type,
    parse_value_type,
)

INT = ScalarType(Scalar.INT)
STRING = ScalarType(Scalar.STRING)

SPEC_TYPES = {
    "int": INT,
    "long": ScalarType(Scalar.LONG),
    "double": ScalarType(Scalar.DOUBLE),
    "bool": ScalarType(Scalar.BOOL),
    "string": STRING,
    "char": ScalarType(Scalar.CHAR),
    "int[]": ArrayType(INT),
    "long[]": ArrayType(ScalarType(Scalar.LONG)),
    "double[]": ArrayType(ScalarType(Scalar.DOUBLE)),
    "bool[]": ArrayType(ScalarType(Scalar.BOOL)),
    "char[]": ArrayType(ScalarType(Scalar.CHAR)),
    "string[]": ArrayType(STRING),
    "int[][]": ArrayType(ArrayType(INT)),
    "long[][]": ArrayType(ArrayType(ScalarType(Scalar.LONG))),
    "double[][]": ArrayType(ArrayType(ScalarType(Scalar.DOUBLE))),
    "bool[][]": ArrayType(ArrayType(ScalarType(Scalar.BOOL))),
    "char[][]": ArrayType(ArrayType(ScalarType(Scalar.CHAR))),
    "string[][]": ArrayType(ArrayType(STRING)),
    "list<int>": ListType(INT),
    "list<long>": ListType(ScalarType(Scalar.LONG)),
    "list<double>": ListType(ScalarType(Scalar.DOUBLE)),
    "list<bool>": ListType(ScalarType(Scalar.BOOL)),
    "list<char>": ListType(ScalarType(Scalar.CHAR)),
    "list<string>": ListType(STRING),
    "list<int[]>": ListType(ArrayType(INT)),
    "list<list<int>>": ListType(ListType(INT)),
    "list<list<string>>": ListType(ListType(STRING)),
    "ListNode": NodeType(NodeKind.LIST_NODE),
    "TreeNode": NodeType(NodeKind.TREE_NODE),
    "GraphNode": NodeType(NodeKind.GRAPH_NODE),
    "ListNode[]": ArrayType(NodeType(NodeKind.LIST_NODE)),
    "list<TreeNode>": ListType(NodeType(NodeKind.TREE_NODE)),
}

GRAMMAR_TYPES = {
    "TreeNode[]": ArrayType(NodeType(NodeKind.TREE_NODE)),
    "GraphNode[]": ArrayType(NodeType(NodeKind.GRAPH_NODE)),
    "list<ListNode>": ListType(NodeType(NodeKind.LIST_NODE)),
    "list<GraphNode>": ListType(NodeType(NodeKind.GRAPH_NODE)),
    "list<list<list<int>>>": ListType(ListType(ListType(INT))),
    "list<list<int[]>>": ListType(ListType(ArrayType(INT))),
    "list<list<TreeNode>>": ListType(ListType(NodeType(NodeKind.TREE_NODE))),
}

ALL_TYPES = {**SPEC_TYPES, **GRAMMAR_TYPES}


@pytest.mark.parametrize(("text", "expected"), ALL_TYPES.items(), ids=list(ALL_TYPES))
def test_parses_every_type_in_the_grammar(text, expected):
    assert parse_value_type(text) == expected


@pytest.mark.parametrize("text", ALL_TYPES)
def test_renders_back_to_canonical_text(text):
    assert str(parse_value_type(text)) == text


@pytest.mark.parametrize("text", ALL_TYPES)
def test_every_value_type_is_a_valid_return_type(text):
    assert parse_return_type(text) == ALL_TYPES[text]


def test_void_is_a_return_type():
    assert parse_return_type("void") == VoidType()


def test_void_renders_as_void():
    assert str(VoidType()) == "void"


@pytest.mark.parametrize(
    ("text", "offset", "reason"),
    [
        ("", 0, "expected a type name"),
        (" int", 0, "expected a type name"),
        ("int ", 3, 'unexpected " "'),
        ("integer", 0, 'unknown type "integer"'),
        ("Int", 0, 'unknown type "Int"'),
        ("List<int>", 0, 'unknown type "List"'),
        ("void", 0, '"void" is only allowed as a return type'),
        ("int[", 4, 'expected "]"'),
        ("int[x", 4, 'expected "]"'),
        ("int]", 3, 'unexpected "]"'),
        ("int[]x", 5, 'unexpected "x"'),
        ("int[][][]", 7, '"int[][][]" is not a valid type'),
        ("ListNode[][]", 10, '"ListNode[][]" is not a valid type'),
        ("list", 4, 'expected "<"'),
        ("list <int>", 4, 'expected "<"'),
        ("list<", 5, "expected a type name"),
        ("list<>", 5, "expected a type name"),
        ("list<int", 8, 'expected ">"'),
        ("list<int>>", 9, 'unexpected ">"'),
        ("list<int>[]", 9, 'unexpected "["'),
        ("list<int,int>", 8, 'expected ">"'),
        ("list<void>", 5, '"void" is only allowed as a return type'),
        ("list<int[][]>", 10, '"int[][]" is not allowed as a list element'),
        ("list<ListNode[]>", 13, '"ListNode[]" is not allowed as a list element'),
        ("list<list<list<list<int>>>>", 15, "nesting deeper than 3 levels"),
        ("list<list<list<int[]>>>", 18, "nesting deeper than 3 levels"),
    ],
)
def test_rejects_invalid_type_with_offset_and_reason(text, offset, reason):
    with pytest.raises(TypeSyntaxError) as raised:
        parse_value_type(text)
    assert (raised.value.offset, raised.value.reason) == (offset, reason)


def test_return_type_errors_point_into_the_text():
    with pytest.raises(TypeSyntaxError) as raised:
        parse_return_type("voids")
    assert raised.value.reason == 'unknown type "voids"'


def test_error_message_quotes_text_and_one_based_column():
    with pytest.raises(TypeSyntaxError) as raised:
        parse_value_type("list<int")
    assert str(raised.value) == 'invalid type "list<int": expected ">" at column 9'


def test_syntax_error_is_a_value_error():
    with pytest.raises(ValueError, match="invalid type"):
        parse_value_type("map<int>")
