"""TypeScript stubs (docs/specs/runners.md#stub-generation).

Types follow the TypeScript column of docs/specs/problem-format.md#type-mapping; the text matches
Prettier's defaults (2-space indent, 80 columns, parameters wrapped one per line with a trailing
comma when a declaration is wider), so no formatter needs to run.
"""

from collections.abc import Iterator, Mapping

from coding_study.domain.concurrency import model_text
from coding_study.domain.layout import statement_path
from coding_study.domain.naming import member_name
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import ClassSignature, FunctionSignature, Method, Param
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
)

INDENT = "  "
PRINT_WIDTH = 80
NOT_IMPLEMENTED = 'throw new Error("Not implemented");'
SUPPORT_MODULE = "#support"
SUPPORT_CLASSES = (NodeKind.LIST_NODE, NodeKind.TREE_NODE, NodeKind.GRAPH_NODE)
"""Import order in stubs."""

_SCALAR_TYPES: Mapping[Scalar, str] = {
    Scalar.INT: "number",
    Scalar.LONG: "number",
    Scalar.DOUBLE: "number",
    Scalar.BOOL: "boolean",
    Scalar.STRING: "string",
    Scalar.CHAR: "string",
}


class TypeScriptStubGenerator:
    """`StubGenerator` for `typescript/practice/<slug>.ts`."""

    def generate(self, meta: ProblemMeta) -> str:
        lines = [_header(meta)]
        if meta.concurrency is not None:
            lines.append(f"// Concurrency: {model_text(meta.concurrency, Language.TYPESCRIPT)}")
        imports = _support_imports(meta)
        if imports:
            lines += [f'import {{ {", ".join(imports)} }} from "{SUPPORT_MODULE}";', ""]
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


def _support_imports(meta: ProblemMeta) -> list[str]:
    used = {kind for declared in _declared_types(meta) for kind in _node_kinds(declared)}
    return [kind.value for kind in SUPPORT_CLASSES if kind in used]


def _declared_types(meta: ProblemMeta) -> Iterator[ReturnType]:
    signature = meta.signature
    if isinstance(signature, FunctionSignature):
        yield from (param.type for param in signature.params)
        yield signature.returns.type
        return
    yield from (param.type for param in signature.constructor_params)
    for method in signature.methods:
        yield from (param.type for param in method.params)
        yield method.returns.type


def _node_kinds(declared: ReturnType) -> Iterator[NodeKind]:
    match declared:
        case NodeType(kind):
            yield kind
        case ArrayType(element) | ListType(element):
            yield from _node_kinds(element)
        case _:
            pass


def _function(signature: FunctionSignature) -> list[str]:
    name = member_name(signature.name, Language.TYPESCRIPT)
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
    name = member_name(method.name, Language.TYPESCRIPT)
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
    return f"{member_name(param.name, Language.TYPESCRIPT)}: {typescript_type(param.type)}"
