"""Rust stubs (docs/specs/runners.md#stub-generation).

Types follow the Rust column of docs/specs/problem-format.md#go-and-rust-mapping, the way
LeetCode writes them: owned parameters, `&mut` for an `output_from` parameter, `pub struct` with
`pub fn new(...) -> Self` and `&mut self` methods (`&self` for concurrent problems, whose
instance threads share). Node types come from the `cs_support` crate, `decimal` is
`rust_decimal::Decimal` and `date` is `chrono::NaiveDate`; each is imported only when the
signature uses it, in one group after the `Rc` and `RefCell` imports that trees and graphs need.
The
text is already rustfmt-clean, including rustfmt's split of a signature longer than 100
characters, so no formatter needs to run.
"""

from coding_study.adapters.languages.rust.types import (
    SHARED_NODES,
    crate_imports,
    node_kinds,
    rust_type,
)
from coding_study.domain.concurrency import model_text
from coding_study.domain.layout import statement_path
from coding_study.domain.naming import NameRole, member_name
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import ClassSignature, FunctionSignature, Method, Param
from coding_study.domain.type_dsl import ReturnType

INDENT = "    "
NOT_IMPLEMENTED = "todo!()"
MAX_WIDTH = 100
"""rustfmt's default `max_width`."""
STD_IMPORTS = ("use std::cell::RefCell;", "use std::rc::Rc;")


class RustStubGenerator:
    """`StubGenerator` for `rust/practice/<snake_slug>.rs`."""

    def generate(self, meta: ProblemMeta) -> str:
        lines = [_header(meta)]
        if meta.concurrency is not None:
            lines.append(f"// Concurrency: {model_text(meta.concurrency, Language.RUST)}")
        lines += _imports(meta)
        lines.append("")
        if isinstance(meta.signature, ClassSignature):
            lines += _class(meta.signature, shared=meta.concurrency is not None)
        else:
            lines += _function(meta.signature)
        return "\n".join(lines) + "\n"


def _header(meta: ProblemMeta) -> str:
    return f"// {meta.title}. Statement: {statement_path(meta.slug)}. Run: cstudy test {meta.slug}"


def _imports(meta: ProblemMeta) -> list[str]:
    crates = crate_imports(meta.signature)
    if not crates:
        return []
    standard = ["", *STD_IMPORTS] if node_kinds(meta.signature) & SHARED_NODES else []
    return [*standard, "", *crates]


def _function(signature: FunctionSignature) -> list[str]:
    name = member_name(signature.name, Language.RUST, NameRole.FUNCTION)
    params = [_param(param, signature.returns.output_from) for param in signature.params]
    head = _head(f"pub fn {name}", params, signature.returns.type, "")
    return [*head, f"{INDENT}{NOT_IMPLEMENTED}", "}"]


def _class(signature: ClassSignature, shared: bool) -> list[str]:
    name = signature.name
    constructor_params = [_param(param, None) for param in signature.constructor_params]
    receiver = "&self" if shared else "&mut self"
    lines = [
        f"pub struct {name} {{}}",
        "",
        f"impl {name} {{",
        *_head("pub fn new", constructor_params, None, INDENT),
        f"{INDENT * 2}{name} {{}}",
        f"{INDENT}}}",
    ]
    for method in signature.methods:
        lines += ["", *_method(method, receiver)]
    return [*lines, "}"]


def _method(method: Method, receiver: str) -> list[str]:
    level = [] if method.level is None else [f"{INDENT}// Level {method.level}"]
    name = member_name(method.name, Language.RUST, NameRole.METHOD)
    params = [receiver, *(_param(param, method.returns.output_from) for param in method.params)]
    head = _head(f"pub fn {name}", params, method.returns.type, INDENT)
    return [*level, *head, f"{INDENT * 2}{NOT_IMPLEMENTED}", f"{INDENT}}}"]


def _head(name: str, params: list[str], returns: ReturnType | None, indent: str) -> list[str]:
    """The signature line, or rustfmt's vertical layout when the line is too long. A constructor
    (`returns` None) returns `Self`."""
    result = "Self" if returns is None else rust_type(returns)
    tail = f" -> {result} {{" if result else " {"
    line = f"{indent}{name}({', '.join(params)}){tail}"
    if len(line) <= MAX_WIDTH:
        return [line]
    return [
        f"{indent}{name}(",
        *(f"{indent}{INDENT}{param}," for param in params),
        f"{indent}){tail}",
    ]


def _param(param: Param, output_from: str | None) -> str:
    name = member_name(param.name, Language.RUST, NameRole.PARAMETER)
    mutable = "&mut " if param.name == output_from else ""
    return f"{name}: {mutable}{rust_type(param.type)}"
