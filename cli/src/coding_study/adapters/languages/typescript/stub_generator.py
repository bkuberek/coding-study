"""TypeScript stubs (docs/specs/runners.md#stub-generation).

Types follow the TypeScript column of docs/specs/problem-format.md#type-mapping; the text matches
Prettier's defaults (2-space indent, 80 columns, parameters wrapped one per line with a trailing
comma when a declaration is wider), so no formatter needs to run.
"""

from collections.abc import Iterator, Mapping

from coding_study.domain.concurrency import model_text
from coding_study.domain.layout import statement_path
from coding_study.domain.naming import NameRole, member_name
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    declared_types,
)
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeKind,
    NodeType,
    ReturnType,
    Scalar,
    ScalarType,
    ValueType,
    VoidType,
    scalars_of,
)

INDENT = "  "
PRINT_WIDTH = 80
NOT_IMPLEMENTED = 'throw new Error("Not implemented");'
SUPPORT_MODULE = "#support"
SUPPORT_CLASSES = (NodeKind.LIST_NODE, NodeKind.TREE_NODE, NodeKind.GRAPH_NODE)
"""Node classes in import order in stubs."""
DECIMAL_CLASS = "Decimal"
"""Imported after the node classes when the signature uses `decimal`."""
ISO_DATE_TYPE = "IsoDate"
"""`type IsoDate = string`, imported last, type-only (`verbatimModuleSyntax`), for `date`."""

_SCALAR_TYPES: Mapping[Scalar, str] = {
    Scalar.INT: "number",
    Scalar.LONG: "number",
    Scalar.DOUBLE: "number",
    Scalar.BOOL: "boolean",
    Scalar.STRING: "string",
    Scalar.CHAR: "string",
    Scalar.DECIMAL: DECIMAL_CLASS,
    Scalar.DATE: ISO_DATE_TYPE,
}


class TypeScriptStubGenerator:
    """`StubGenerator` for `typescript/practice/<slug>.ts`."""

    def generate(self, meta: ProblemMeta) -> str:
        lines = [_header(meta)]
        if meta.concurrency is not None:
            lines.append(f"// Concurrency: {model_text(meta.concurrency, Language.TYPESCRIPT)}")
        import_line = _support_import(meta)
        if import_line:
            lines += [import_line, ""]
        if isinstance(meta.signature, ClassSignature):
            lines += _class(meta.signature)
        else:
            lines += _function(meta.signature)
        return "\n".join(lines) + "\n"


def typescript_type(declared: ReturnType) -> str:
    match declared:
        case ScalarType(scalar):
            return _SCALAR_TYPES[scalar]
        case NodeType(kind):
            return f"{kind} | null"
        case ArrayType(element) | ListType(element):
            return f"{_element_type(element)}[]"
        case VoidType():
            return "void"


def _element_type(element: ValueType) -> str:
    """Union element types need parentheses: `(ListNode | null)[]`."""
    text = typescript_type(element)
    return f"({text})" if isinstance(element, NodeType) else text


def _header(meta: ProblemMeta) -> str:
    return f"// {meta.title}. Statement: {statement_path(meta.slug)}. Run: cstudy test {meta.slug}"


def _support_import(meta: ProblemMeta) -> str | None:
    """`import { ListNode, Decimal, type IsoDate } from "#support";`. A stub that needs only the
    `IsoDate` type uses `import type`, which `verbatimModuleSyntax` erases completely.
    """
    declared = list(declared_types(meta.signature))
    kinds = {kind for value_type in declared for kind in _node_kinds(value_type)}
    scalars = {scalar for value_type in declared for scalar in scalars_of(value_type)}
    classes = [kind.value for kind in SUPPORT_CLASSES if kind in kinds]
    if Scalar.DECIMAL in scalars:
        classes.append(DECIMAL_CLASS)
    if Scalar.DATE not in scalars:
        return _import_line("import", classes) if classes else None
    if not classes:
        return _import_line("import type", [ISO_DATE_TYPE])
    return _import_line("import", [*classes, f"type {ISO_DATE_TYPE}"])


def _import_line(keyword: str, names: list[str]) -> str:
    return f'{keyword} {{ {", ".join(names)} }} from "{SUPPORT_MODULE}";'


def _node_kinds(declared: ReturnType) -> Iterator[NodeKind]:
    match declared:
        case NodeType(kind):
            yield kind
        case ArrayType(element) | ListType(element):
            yield from _node_kinds(element)
        case _:
            pass


def _function(signature: FunctionSignature) -> list[str]:
    name = member_name(signature.name, Language.TYPESCRIPT, NameRole.FUNCTION)
    returns = typescript_type(signature.returns.type)
    head = _declaration(f"export function {name}", signature.params, f": {returns} {{", "")
    return [*head, f"{INDENT}{NOT_IMPLEMENTED}", "}"]


def _class(signature: ClassSignature) -> list[str]:
    lines = [f"export class {signature.name} {{"]
    lines += _declaration("constructor", signature.constructor_params, " {}", INDENT)
    for method in signature.methods:
        lines += ["", *_method(method)]
    return [*lines, "}"]


def _method(method: Method) -> list[str]:
    """TypeScript concurrent problems use the async model: `blocking` methods are async."""
    level = [] if method.level is None else [f"{INDENT}// Level {method.level}"]
    name = member_name(method.name, Language.TYPESCRIPT, NameRole.METHOD)
    returns = typescript_type(method.returns.type)
    if method.blocking:
        name, returns = f"async {name}", f"Promise<{returns}>"
    head = _declaration(name, method.params, f": {returns} {{", INDENT)
    return [*level, *head, f"{INDENT * 2}{NOT_IMPLEMENTED}", f"{INDENT}}}"]


def _declaration(prefix: str, params: tuple[Param, ...], suffix: str, indent: str) -> list[str]:
    """`prefix(params)suffix` on one line, or with one parameter per line when too wide."""
    rendered = [_param(param) for param in params]
    line = f"{indent}{prefix}({', '.join(rendered)}){suffix}"
    if len(line) <= PRINT_WIDTH or not rendered:
        return [line]
    return [
        f"{indent}{prefix}(",
        *(f"{indent}{INDENT}{param}," for param in rendered),
        f"{indent}){suffix}",
    ]


def _param(param: Param) -> str:
    name = member_name(param.name, Language.TYPESCRIPT, NameRole.PARAMETER)
    return f"{name}: {typescript_type(param.type)}"
