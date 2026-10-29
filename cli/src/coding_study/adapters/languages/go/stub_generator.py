"""Go stubs (docs/specs/runners.md#stub-generation).

Types follow the Go column of docs/specs/problem-format.md#go-and-rust-mapping. Each problem is
its own package, `package <snake_slug>`, which is also the package clause of reference and buggy
files, so a file moves between `solutions/` and the practice directory unchanged. Node types are
aliases of the runner's `cstudy/support` types. `decimal` is the vendored shopspring/decimal
package and `date` the standard `time` package. Each package is imported only when the signature
uses it (Go rejects unused imports), grouped the way goimports groups them. The text is already
gofmt-clean, so no formatter needs to run.
"""

import re
from collections.abc import Iterator, Mapping

from coding_study.domain.concurrency import model_text
from coding_study.domain.layout import statement_path
from coding_study.domain.naming import NameRole, constructor_name, member_name
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
    VoidType,
    scalars_of,
)

INDENT = "\t"
NOT_IMPLEMENTED = 'panic("not implemented")'
SUPPORT_PACKAGE = "cstudy/support"
SUPPORT_NAME = "support"
SUPPORT_CLASSES = (NodeKind.LIST_NODE, NodeKind.TREE_NODE, NodeKind.GRAPH_NODE)
"""Node types in declaration order in stubs."""
SCALAR_PACKAGES: Mapping[Scalar, str] = {
    Scalar.DECIMAL: "github.com/shopspring/decimal",
    Scalar.DATE: "time",
}
"""The package each scalar's Go type comes from."""
FALLBACK_RECEIVER = "recv"
_PASCAL_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")

_SCALAR_TYPES: Mapping[Scalar, str] = {
    Scalar.INT: "int",
    Scalar.LONG: "int64",
    Scalar.DOUBLE: "float64",
    Scalar.BOOL: "bool",
    Scalar.STRING: "string",
    Scalar.CHAR: "rune",
    Scalar.DECIMAL: "decimal.Decimal",
    Scalar.DATE: "time.Time",
}


class GoStubGenerator:
    """`StubGenerator` for `go/practice/<snake_slug>/<snake_slug>.go` (`layout.go_file_name`)."""

    def generate(self, meta: ProblemMeta) -> str:
        lines = [_header(meta)]
        if meta.concurrency is not None:
            lines.append(f"// Concurrency: {model_text(meta.concurrency, Language.GO)}")
        lines += ["", f"package {meta.snake_slug}", *_imports(meta), *_aliases(meta), ""]
        if isinstance(meta.signature, ClassSignature):
            lines += _class(meta.signature)
        else:
            lines += _function(meta.signature)
        return "\n".join(lines) + "\n"


def go_type(declared: ReturnType) -> str:
    """The Go spelling of a DSL type; empty for void (no result)."""
    match declared:
        case ScalarType(scalar):
            return _SCALAR_TYPES[scalar]
        case NodeType(kind):
            return f"*{kind}"
        case ArrayType(element) | ListType(element):
            return f"[]{go_type(element)}"
        case VoidType():
            return ""


def _header(meta: ProblemMeta) -> str:
    return f"// {meta.title}. Statement: {statement_path(meta.slug)}. Run: cstudy test {meta.slug}"


def _imports(meta: ProblemMeta) -> list[str]:
    """The packages the signature uses: one `import` line for a single package, otherwise a
    block whose first group holds the paths without a domain (`time`, `cstudy/support`), as
    goimports writes it."""
    declared = declared_types(meta.signature)
    scalars = {scalar for value_type in declared for scalar in scalars_of(value_type)}
    paths = [path for scalar, path in SCALAR_PACKAGES.items() if scalar in scalars]
    if _node_kinds_used(meta):
        paths.append(SUPPORT_PACKAGE)
    if not paths:
        return []
    if len(paths) == 1:
        return ["", f'import "{paths[0]}"']
    local = sorted(path for path in paths if not _has_domain(path))
    hosted = sorted(path for path in paths if _has_domain(path))
    gap = [""] if local and hosted else []
    return ["", "import (", *_quoted(local), *gap, *_quoted(hosted), ")"]


def _has_domain(path: str) -> bool:
    return "." in path.split("/")[0]


def _quoted(paths: list[str]) -> list[str]:
    return [f'{INDENT}"{path}"' for path in paths]


def _aliases(meta: ProblemMeta) -> list[str]:
    """One alias per node type the signature uses, so the body reads `*ListNode`."""
    used = _node_kinds_used(meta)
    if not used:
        return []
    return ["", *(f"type {kind} = {SUPPORT_NAME}.{kind}" for kind in used)]


def _node_kinds_used(meta: ProblemMeta) -> list[NodeKind]:
    kinds = {kind for declared in declared_types(meta.signature) for kind in _node_kinds(declared)}
    return [kind for kind in SUPPORT_CLASSES if kind in kinds]


def _node_kinds(declared: ReturnType) -> Iterator[NodeKind]:
    match declared:
        case NodeType(kind):
            yield kind
        case ArrayType(element) | ListType(element):
            yield from _node_kinds(element)
        case _:
            pass


def _function(signature: FunctionSignature) -> list[str]:
    name = member_name(signature.name, Language.GO, NameRole.FUNCTION)
    head = f"func {name}({_params(signature.params)}){_result(signature.returns.type)} {{"
    return [head, f"{INDENT}{NOT_IMPLEMENTED}", "}"]


def _class(signature: ClassSignature) -> list[str]:
    name = signature.name
    constructor = constructor_name(name, Language.GO)
    receiver = _receiver(signature)
    lines = [
        f"type {name} struct{{}}",
        "",
        f"func {constructor}({_params(signature.constructor_params)}) *{name} {{",
        f"{INDENT}return &{name}{{}}",
        "}",
    ]
    for method in signature.methods:
        lines += ["", *_method(method, f"{receiver} *{name}")]
    return lines


def _method(method: Method, receiver: str) -> list[str]:
    level = [] if method.level is None else [f"// Level {method.level}"]
    name = member_name(method.name, Language.GO, NameRole.METHOD)
    head = f"func ({receiver}) {name}({_params(method.params)}){_result(method.returns.type)} {{"
    return [*level, head, f"{INDENT}{NOT_IMPLEMENTED}", "}"]


def _receiver(signature: ClassSignature) -> str:
    """A short receiver named after the type's last word (`c` for LRUCache), unless a parameter
    of a method already has that name."""
    words = _PASCAL_WORDS.findall(signature.name)
    taken = {
        member_name(param.name, Language.GO, NameRole.PARAMETER)
        for method in signature.methods
        for param in method.params
    }
    candidates = (words[-1][:1].lower(), signature.name[:1].lower(), FALLBACK_RECEIVER)
    return next(candidate for candidate in candidates if candidate not in taken)


def _params(params: tuple[Param, ...]) -> str:
    return ", ".join(_param(param) for param in params)


def _param(param: Param) -> str:
    return f"{member_name(param.name, Language.GO, NameRole.PARAMETER)} {go_type(param.type)}"


def _result(returns: ReturnType) -> str:
    text = go_type(returns)
    return f" {text}" if text else ""
