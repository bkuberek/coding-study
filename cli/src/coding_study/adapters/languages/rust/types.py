"""The Rust column of docs/specs/problem-format.md#go-and-rust-mapping and the spelling of names,
shared by the stub generator and the bridge generator."""

from collections.abc import Iterator, Mapping

from coding_study.domain.naming import NameRole, member_name, rust_identifier
from coding_study.domain.problem import Language
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
    Scalar.DECIMAL: "Decimal",
    Scalar.DATE: "NaiveDate",
}
SCALAR_IMPORTS: Mapping[Scalar, str] = {
    Scalar.DATE: "use chrono::NaiveDate;",
    Scalar.DECIMAL: "use rust_decimal::Decimal;",
}
"""The vendored crate type behind each scalar that is not a primitive."""


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


def rust_name(canonical: str, role: NameRole) -> str:
    """A function, method or parameter as Rust source declares and calls it: snake_case, and a
    keyword as a raw identifier (`r#move`)."""
    return rust_identifier(member_name(canonical, Language.RUST, role))


def crate_imports(signature: Signature) -> list[str]:
    """The `use` lines of the crates outside the standard library that the signature needs
    (`chrono`, `cs_support`, `rust_decimal`), in the order rustfmt sorts one group."""
    used = {scalar for declared in declared_types(signature) for scalar in scalars_of(declared)}
    lines = [line for scalar, line in SCALAR_IMPORTS.items() if scalar in used]
    names = sorted(str(kind) for kind in node_kinds(signature))
    if names:
        listed = names[0] if len(names) == 1 else "{" + ", ".join(names) + "}"
        lines.append(f"use {SUPPORT_CRATE}::{listed};")
    return sorted(lines)


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
