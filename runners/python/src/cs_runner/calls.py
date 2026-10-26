"""One call of a function, constructor or method: its arguments and how its result is encoded.

Modifiers (docs/specs/problem-format.md#modifiers) resolve against the arguments as decoded,
before the call: `ref_of` picks a node of another parameter, and `as: index` and
`no_alias_with` compare the result with the nodes a parameter held, even if the call relinked
them.
"""

from collections.abc import Iterable, Mapping
from typing import cast

from cs_runner.codec import decode, encode
from cs_runner.dsl import NodeType, ReturnType, SequenceType, ValueType, VoidType
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.json_value import Json
from cs_runner.nodes import node_value, traverse
from cs_runner.request import Member, NodeSerialization, Param

NULL_INDEX = -1
"""`as: index` encodes a null result as -1."""


class BoundCall:
    def __init__(
        self, member: Member, arguments: dict[str, object], nodes_before: dict[str, list[object]]
    ) -> None:
        self._member = member
        self._arguments = arguments
        self._nodes_before = nodes_before

    @property
    def arguments(self) -> list[object]:
        """Positional arguments in declared parameter order."""
        return list(self._arguments.values())

    def encode_result(self, result: object) -> Json:
        returns = self._member.returns
        if returns.output_from is not None:
            return self._encode_parameter(self._member.param(returns.output_from))
        if isinstance(returns.type, VoidType):
            return None
        match returns.serialize_as:
            case NodeSerialization.VALUE:
                return None if result is None else node_value(result)
            case NodeSerialization.INDEX:
                return self._index_in_parameter(result)
            case None:
                return self._encode_value(result, returns.type)

    def _encode_parameter(self, param: Param) -> Json:
        return encode(self._arguments[param.name], param.type)

    def _index_in_parameter(self, result: object) -> int:
        if result is None:
            return NULL_INDEX
        parameter = cast("str", self._member.returns.index_of)
        nodes = self._nodes_before[parameter]
        index = next((index for index, node in enumerate(nodes) if node is result), None)
        if index is None:
            raise InvalidOutputError(f'the returned node is not a node of "{parameter}"')
        return index

    def _encode_value(self, result: object, value_type: ValueType) -> Json:
        encoded = encode(result, value_type)
        parameter = self._member.returns.no_alias_with
        if parameter is not None:
            self._check_no_alias(result, value_type, parameter)
        return encoded

    def _check_no_alias(self, result: object, value_type: ValueType, parameter: str) -> None:
        inputs = {id(node) for node in self._nodes_before[parameter]}
        if any(id(node) in inputs for node in nodes_in(result, value_type)):
            raise InvalidOutputError(f'the returned structure shares nodes with "{parameter}"')


def bind(member: Member, values: Mapping[str, Json]) -> BoundCall:
    """Decode a call's arguments from input values keyed by canonical parameter name."""
    missing = [param.name for param in member.params if param.name not in values]
    if missing:
        raise CaseInputError(f"missing input {', '.join(missing)}")
    arguments = {
        param.name: decode(values[param.name], param.type)
        for param in member.params
        if param.ref_of is None
    }
    nodes_before = {
        name: nodes_in(arguments[name], member.param(name).type)
        for name in _parameters_needing_nodes(member)
    }
    for param in member.params:
        if param.ref_of is not None:
            arguments[param.name] = _node_with_value(values[param.name], param.ref_of, nodes_before)
    ordered = {param.name: arguments[param.name] for param in member.params}
    return BoundCall(member, ordered, nodes_before)


def nodes_in(value: object, value_type: ReturnType) -> list[object]:
    """Every node reachable from `value`, which may also be an array or list of nodes."""
    match value_type:
        case NodeType(kind):
            return traverse(value, kind)
        case SequenceType(element):
            items = cast("Iterable[object]", value)
            return [node for item in items for node in nodes_in(item, element)]
        case _:
            return []


def _parameters_needing_nodes(member: Member) -> set[str]:
    returns = member.returns
    named = {returns.index_of, returns.no_alias_with, *(param.ref_of for param in member.params)}
    return {name for name in named if name is not None}


def _node_with_value(value: Json, parameter: str, nodes: Mapping[str, list[object]]) -> object:
    if value is None:
        return None
    candidates = nodes[parameter]
    node = next((node for node in candidates if getattr(node, "val", None) == value), None)
    if node is None:
        raise CaseInputError(f'no node with value {value} in "{parameter}"')
    return node
