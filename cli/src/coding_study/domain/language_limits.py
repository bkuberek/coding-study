"""What a language cannot express, so a problem must not list it (`cstudy verify` S13,
docs/specs/authoring.md#static).

Rust lists are LeetCode's `Option<Box<ListNode>>`: each node has one owner, so a list cannot be
cyclic, and `ref_of` or `as: index` cannot name one of its nodes, which would need a second
reference to it (docs/specs/problem-format.md#go-and-rust-mapping).
"""

from collections.abc import Iterator, Sequence

from coding_study.domain.cases import Case, FunctionInput, JsonValue, OperationSequence
from coding_study.domain.problem import Language
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    Signature,
)
from coding_study.domain.type_dsl import ArrayType, ListType, NodeKind, NodeType, ReturnType

LIST_IDENTITY = (
    "ref_of and as: index cannot name the nodes of a ListNode in Rust: an Option<Box<ListNode>> "
    "has one owner per node"
)
CYCLIC_LIST = (
    "a cyclic ListNode input cannot be built in Rust: an Option<Box<ListNode>> cannot point back"
)
CYCLE_FIELD = "cycle_at"


def language_limits(
    signature: Signature, cases: Sequence[Case], language: Language
) -> tuple[str, ...]:
    """Why `language` cannot run a problem with `signature` and `cases`; empty when it can."""
    if language is not Language.RUST:
        return ()
    reasons: list[str] = []
    if names_list_nodes(signature):
        reasons.append(LIST_IDENTITY)
    if any(_cyclic_input(signature, case) for case in cases):
        reasons.append(CYCLIC_LIST)
    return tuple(reasons)


def names_list_nodes(signature: Signature) -> bool:
    """Whether a `ref_of` points into a list, or an `as: index` result is a list node."""
    return any(_member_names_list_nodes(member) for member in _members(signature))


def _members(signature: Signature) -> Iterator[FunctionSignature | Method]:
    if isinstance(signature, FunctionSignature):
        yield signature
    else:
        yield from signature.methods


def _member_names_list_nodes(member: FunctionSignature | Method) -> bool:
    params = {param.name: param.type for param in member.params}
    referenced = [params.get(param.ref_of) for param in member.params if param.ref_of]
    returns = member.returns
    indexed = [returns.type, params.get(returns.index_of)] if returns.index_of else []
    return any(_holds_lists(declared) for declared in [*referenced, *indexed] if declared)


def _holds_lists(declared: ReturnType) -> bool:
    match declared:
        case NodeType(kind):
            return kind is NodeKind.LIST_NODE
        case ArrayType(element) | ListType(element):
            return _holds_lists(element)
        case _:
            return False


def _cyclic_input(signature: Signature, case: Case) -> bool:
    match case.input:
        case FunctionInput(arguments) if isinstance(signature, FunctionSignature):
            return any(_cyclic(arguments.get(param.name), param.type) for param in signature.params)
        case OperationSequence(ops, args) if isinstance(signature, ClassSignature):
            return any(
                _cyclic_arguments(_params(signature, index, op), values)
                for index, (op, values) in enumerate(zip(ops, args, strict=False))
            )
        case _:
            return False


def _params(signature: ClassSignature, index: int, op: str) -> tuple[Param, ...]:
    if index == 0:
        return signature.constructor_params
    method = next((method for method in signature.methods if method.name == op), None)
    return method.params if method else ()


def _cyclic_arguments(params: Sequence[Param], values: Sequence[JsonValue]) -> bool:
    return any(_cyclic(value, param.type) for param, value in zip(params, values, strict=False))


def _cyclic(value: JsonValue | None, declared: ReturnType) -> bool:
    match declared:
        case NodeType(NodeKind.LIST_NODE):
            return isinstance(value, dict) and CYCLE_FIELD in value
        case ArrayType(element) | ListType(element) if isinstance(value, list):
            return any(_cyclic(item, element) for item in value)
        case _:
            return False
