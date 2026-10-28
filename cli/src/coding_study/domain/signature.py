"""Problem signatures (docs/specs/problem-format.md#signatures)."""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.type_dsl import NodeType, ReturnType, ValueType, VoidType


class NodeSerialization(StrEnum):
    """The `as` modifier on a node-typed return."""

    VALUE = "value"
    INDEX = "index"


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    type: ValueType
    ref_of: str | None = None


@dataclass(frozen=True, slots=True)
class Returns:
    type: ReturnType
    output_from: str | None = None
    serialize_as: NodeSerialization | None = None
    index_of: str | None = None
    no_alias_with: str | None = None


@dataclass(frozen=True, slots=True)
class FunctionSignature:
    name: str
    params: tuple[Param, ...]
    returns: Returns


@dataclass(frozen=True, slots=True)
class Method:
    name: str
    params: tuple[Param, ...]
    returns: Returns
    level: int | None = None
    blocking: bool = False
    """Concurrent problems: the method may wait for another worker."""


@dataclass(frozen=True, slots=True)
class ClassSignature:
    name: str
    constructor_params: tuple[Param, ...]
    methods: tuple[Method, ...]


type Signature = FunctionSignature | ClassSignature


def declared_types(signature: Signature) -> Iterator[ReturnType]:
    """Every parameter and return type, in declaration order (constructor first for a class)."""
    if isinstance(signature, FunctionSignature):
        yield from (param.type for param in signature.params)
        yield signature.returns.type
        return
    yield from (param.type for param in signature.constructor_params)
    for method in signature.methods:
        yield from (param.type for param in method.params)
        yield method.returns.type


def output_type(member: FunctionSignature | Method) -> ValueType | None:
    """The type of the value a call's expected output holds: the return type, or the type of the
    `output_from` parameter. None for `void`, and for a node returned `as` a value or an index.
    """
    returns = member.returns
    if returns.output_from is not None:
        sources = (param.type for param in member.params if param.name == returns.output_from)
        return next(sources, None)
    if isinstance(returns.type, VoidType) or returns.serialize_as is not None:
        return None
    return returns.type


@dataclass(frozen=True, slots=True)
class SignatureIssue:
    """A modifier that the JSON Schema accepts but the signature cannot honor."""

    location: str
    message: str


def modifier_issues(signature: Signature) -> tuple[SignatureIssue, ...]:
    """Cross-checks of the modifiers (docs/specs/problem-format.md#modifiers).

    Modifiers resolve against the parameters of their own function, constructor or method.
    """
    if isinstance(signature, FunctionSignature):
        return _member_issues(signature.params, signature.returns, "signature.function")
    location = "signature.class"
    issues = list(_param_issues(signature.constructor_params, f"{location}.constructor.params"))
    for index, method in enumerate(signature.methods):
        issues += _member_issues(method.params, method.returns, f"{location}.methods[{index}]")
    return tuple(issues)


def blocking_issues(signature: Signature) -> tuple[SignatureIssue, ...]:
    """`blocking` marks methods of concurrent problems only; the caller knows the kind."""
    if isinstance(signature, FunctionSignature):
        return ()
    return tuple(
        SignatureIssue(
            f"signature.class.methods[{index}].blocking", "only allowed in concurrent problems"
        )
        for index, method in enumerate(signature.methods)
        if method.blocking
    )


def _member_issues(
    params: tuple[Param, ...], returns: Returns, location: str
) -> tuple[SignatureIssue, ...]:
    return (
        *_param_issues(params, f"{location}.params"),
        *_returns_issues(returns, params, f"{location}.returns"),
    )


def _param_issues(params: tuple[Param, ...], location: str) -> list[SignatureIssue]:
    return [
        SignatureIssue(f"{location}[{index}].ref_of", message)
        for index, param in enumerate(params)
        if param.ref_of is not None and (message := _ref_of_problem(param, param.ref_of, params))
    ]


def _ref_of_problem(param: Param, ref_of: str, params: tuple[Param, ...]) -> str | None:
    if not isinstance(param.type, NodeType):
        return f'only allowed on a node-typed parameter, not "{param.type}"'
    if ref_of == param.name:
        return "must name another parameter"
    return _named_param_problem(ref_of, params, param.type)


def _returns_issues(
    returns: Returns, params: tuple[Param, ...], location: str
) -> list[SignatureIssue]:
    checks = {
        "output_from": _output_from_problem(returns, params),
        "as": _as_problem(returns),
        "of": _of_problem(returns, params),
        "no_alias_with": _no_alias_with_problem(returns, params),
    }
    return [
        SignatureIssue(f"{location}.{modifier}", message)
        for modifier, message in checks.items()
        if message is not None
    ]


def _output_from_problem(returns: Returns, params: tuple[Param, ...]) -> str | None:
    if returns.output_from is None:
        return None
    if not isinstance(returns.type, VoidType):
        return f'only allowed with type void, not "{returns.type}"'
    return _named_param_problem(returns.output_from, params)


def _as_problem(returns: Returns) -> str | None:
    if returns.serialize_as is None or isinstance(returns.type, NodeType):
        return None
    return f'only allowed on a node-typed return, not "{returns.type}"'


def _of_problem(returns: Returns, params: tuple[Param, ...]) -> str | None:
    if returns.index_of is None:
        return None
    if returns.serialize_as is not NodeSerialization.INDEX:
        return "only allowed with as: index"
    expected_type = returns.type if isinstance(returns.type, NodeType) else None
    return _named_param_problem(returns.index_of, params, expected_type)


def _no_alias_with_problem(returns: Returns, params: tuple[Param, ...]) -> str | None:
    if returns.no_alias_with is None:
        return None
    return _named_param_problem(returns.no_alias_with, params)


def _named_param_problem(
    name: str, params: tuple[Param, ...], expected_type: NodeType | None = None
) -> str | None:
    """Why `name` cannot be resolved, or None; `expected_type` also requires that node type."""
    named = next((param for param in params if param.name == name), None)
    if named is None:
        return f'no parameter named "{name}"'
    if expected_type is not None and named.type != expected_type:
        return f'"{name}" is "{named.type}", not "{expected_type}"'
    return None
