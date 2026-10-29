"""The Rust column of docs/specs/problem-format.md#go-and-rust-mapping, shared by the stub
generator and the bridge generator."""

from collections.abc import Iterator, Mapping

from coding_study.domain.signature import Signature, declared_types
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeKind,
    NodeType,
    ReturnType,
    Scalar,
    ScalarType,
    VoidType,
    scalars_of,
)

UNSUPPORTED_SCALARS = (Scalar.DECIMAL, Scalar.DATE)
"""Planned with vendored libraries (docs/decisions/0012-go-and-rust.md)."""
SUPPORT_CRATE = "cs_support"
SHARED_NODES = frozenset({NodeKind.TREE_NODE, NodeKind.GRAPH_NODE})
"""Node types held as `Rc<RefCell<...>>`, whose stubs import `Rc` and `RefCell`."""

_SCALAR_TYPES: Mapping[Scalar, str] = {
    Scalar.INT: "i32",
    Scalar.LONG: "i64",
    Scalar.DOUBLE: "f64",
    Scalar.BOOL: "bool",
    Scalar.STRING: "String",
    Scalar.CHAR: "char",
}


def rust_type(declared: ReturnType) -> str:
    """The Rust spelling of a DSL type; empty for void (no result). Node types are named as the
    stubs import them."""
    match declared:
        case ScalarType(scalar):
            return _SCALAR_TYPES[scalar]
        case NodeType(kind) if kind in SHARED_NODES:
            return f"Option<Rc<RefCell<{kind}>>>"
        case NodeType(kind):
            return f"Option<Box<{kind}>>"
        case ArrayType(element) | ListType(element):
            return f"Vec<{rust_type(element)}>"
        case VoidType():
            return ""


def unsupported_scalars(signature: Signature) -> list[str]:
    """The scalars of `signature` that Rust does not support yet, in `UNSUPPORTED_SCALARS`
    order."""
    used = {scalar for declared in declared_types(signature) for scalar in scalars_of(declared)}
    return [str(scalar) for scalar in UNSUPPORTED_SCALARS if scalar in used]


def node_kinds(signature: Signature) -> frozenset[NodeKind]:
    """Every node type the signature uses."""
    return frozenset(kind for declared in declared_types(signature) for kind in _kinds(declared))


def _kinds(declared: ReturnType) -> Iterator[NodeKind]:
    match declared:
        case NodeType(kind):
            yield kind
        case ArrayType(element) | ListType(element):
            yield from _kinds(element)
        case ScalarType() | VoidType():
            pass
