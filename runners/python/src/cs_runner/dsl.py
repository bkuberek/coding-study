"""Signature types as the runner reads them (docs/specs/problem-format.md#type-dsl).

Arrays and lists have one Python representation, so `int[]` and `list<int>` both parse to a
`SequenceType`. The CLI validated every signature, so parsing only rejects what cannot be
represented at all.
"""

from dataclasses import dataclass
from enum import StrEnum

ARRAY_SUFFIX = "[]"
LIST_PREFIX = "list<"
LIST_SUFFIX = ">"
VOID = "void"


class Scalar(StrEnum):
    INT = "int"
    LONG = "long"
    DOUBLE = "double"
    BOOL = "bool"
    STRING = "string"
    CHAR = "char"
    DECIMAL = "decimal"
    DATE = "date"


class NodeKind(StrEnum):
    LIST_NODE = "ListNode"
    TREE_NODE = "TreeNode"
    GRAPH_NODE = "GraphNode"


@dataclass(frozen=True, slots=True)
class ScalarType:
    scalar: Scalar


@dataclass(frozen=True, slots=True)
class NodeType:
    kind: NodeKind


@dataclass(frozen=True, slots=True)
class SequenceType:
    """An array (`T[]`) or a list (`list<T>`): a Python list either way."""

    element: "ValueType"


@dataclass(frozen=True, slots=True)
class VoidType:
    pass


type ValueType = ScalarType | NodeType | SequenceType
type ReturnType = ValueType | VoidType


class TypeSyntaxError(ValueError):
    pass


def parse_value_type(text: str) -> ValueType:
    if text.endswith(ARRAY_SUFFIX):
        return SequenceType(parse_value_type(text.removesuffix(ARRAY_SUFFIX)))
    if text.startswith(LIST_PREFIX) and text.endswith(LIST_SUFFIX):
        return SequenceType(parse_value_type(text[len(LIST_PREFIX) : -len(LIST_SUFFIX)]))
    if text in Scalar:
        return ScalarType(Scalar(text))
    if text in NodeKind:
        return NodeType(NodeKind(text))
    raise TypeSyntaxError(f'unknown type "{text}"')


def parse_return_type(text: str) -> ReturnType:
    if text == VOID:
        return VoidType()
    return parse_value_type(text)
