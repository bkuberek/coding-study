"""The signature type DSL (docs/specs/problem-format.md#type-dsl).

Grammar::

    type     := scalar | array | list | node | node "[]"
    scalar   := "int" | "long" | "double" | "bool" | "string" | "char" | "decimal" | "date"
    array    := scalar "[]" | scalar "[][]"
    list     := "list<" elem ">"
    elem     := scalar | scalar "[]" | list | node
    node     := "ListNode" | "TreeNode" | "GraphNode"
    return   := type | "void"

Nesting depth counts every list and array level and is at most 3.
"""

from dataclasses import dataclass
from enum import StrEnum

MAX_NESTING_DEPTH = 3
LIST_KEYWORD = "list"
VOID_KEYWORD = "void"


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

    def __str__(self) -> str:
        return self.scalar.value


@dataclass(frozen=True, slots=True)
class NodeType:
    kind: NodeKind

    def __str__(self) -> str:
        return self.kind.value


@dataclass(frozen=True, slots=True)
class ArrayType:
    element: "ValueType"

    def __str__(self) -> str:
        return f"{self.element}[]"


@dataclass(frozen=True, slots=True)
class ListType:
    element: "ValueType"

    def __str__(self) -> str:
        return f"{LIST_KEYWORD}<{self.element}>"


@dataclass(frozen=True, slots=True)
class VoidType:
    def __str__(self) -> str:
        return VOID_KEYWORD


type ValueType = ScalarType | NodeType | ArrayType | ListType
type ReturnType = ValueType | VoidType


class TypeSyntaxError(ValueError):
    """A type string that does not match the grammar; `offset` is 0-based."""

    def __init__(self, text: str, offset: int, reason: str) -> None:
        super().__init__(f'invalid type "{text}": {reason} at column {offset + 1}')
        self.text = text
        self.offset = offset
        self.reason = reason


def parse_value_type(text: str) -> ValueType:
    return _TypeParser(text).parse()


def parse_return_type(text: str) -> ReturnType:
    if text == VOID_KEYWORD:
        return VoidType()
    return parse_value_type(text)


@dataclass(frozen=True, slots=True)
class _Slot:
    """Where a type appears, which bounds the array dimensions allowed on it."""

    scalar_dimensions: int
    node_dimensions: int
    description: str


_TOP_LEVEL = _Slot(scalar_dimensions=2, node_dimensions=1, description="a valid type")
_LIST_ELEMENT = _Slot(
    scalar_dimensions=1, node_dimensions=0, description="allowed as a list element"
)


class _TypeParser:
    def __init__(self, text: str) -> None:
        self._text = text
        self._offset = 0

    def parse(self) -> ValueType:
        parsed = self._value(_TOP_LEVEL, depth=0)
        if self._offset < len(self._text):
            raise self._error(f'unexpected "{self._current()}"')
        return parsed

    def _value(self, slot: _Slot, depth: int) -> ValueType:
        start = self._offset
        name = self._name()
        if name == LIST_KEYWORD:
            return self._list(start, depth)
        base = self._named_type(name, start)
        return self._array_suffix(base, slot, depth)

    def _list(self, start: int, depth: int) -> ListType:
        self._check_depth(depth + 1, start)
        self._expect("<")
        element = self._value(_LIST_ELEMENT, depth + 1)
        self._expect(">")
        return ListType(element)

    def _named_type(self, name: str, start: int) -> ScalarType | NodeType:
        if name in Scalar:
            return ScalarType(Scalar(name))
        if name in NodeKind:
            return NodeType(NodeKind(name))
        if name == VOID_KEYWORD:
            raise TypeSyntaxError(
                self._text, start, f'"{VOID_KEYWORD}" is only allowed as a return type'
            )
        raise TypeSyntaxError(self._text, start, f'unknown type "{name}"')

    def _array_suffix(self, base: ScalarType | NodeType, slot: _Slot, depth: int) -> ValueType:
        allowed = slot.scalar_dimensions if isinstance(base, ScalarType) else slot.node_dimensions
        parsed: ValueType = base
        dimensions = 0
        while self._current() == "[":
            dimensions += 1
            if dimensions > allowed:
                raise self._error(f'"{parsed}[]" is not {slot.description}')
            self._check_depth(depth + dimensions, self._offset)
            self._offset += 1
            self._expect("]")
            parsed = ArrayType(parsed)
        return parsed

    def _name(self) -> str:
        start = self._offset
        while _is_name_character(self._current()):
            self._offset += 1
        if self._offset == start:
            raise self._error("expected a type name")
        return self._text[start : self._offset]

    def _expect(self, token: str) -> None:
        if self._current() != token:
            raise self._error(f'expected "{token}"')
        self._offset += 1

    def _check_depth(self, depth: int, offset: int) -> None:
        if depth > MAX_NESTING_DEPTH:
            raise TypeSyntaxError(
                self._text, offset, f"nesting deeper than {MAX_NESTING_DEPTH} levels"
            )

    def _current(self) -> str:
        return self._text[self._offset : self._offset + 1]

    def _error(self, reason: str) -> TypeSyntaxError:
        return TypeSyntaxError(self._text, self._offset, reason)


def _is_name_character(character: str) -> bool:
    return character.isascii() and character.isalpha()
