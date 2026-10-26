"""Python stubs (docs/specs/runners.md#stub-generation).

Types follow the Python column of docs/specs/problem-format.md#type-mapping and names follow
`coding_study.domain.naming`. The text already matches `ruff format` with its default line
length, so no formatter runs: a signature too long for one line moves its parameters to an
indented line of their own, or to one line each with a trailing comma when that is still too
long.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from coding_study.domain.concurrency import ConcurrencyModel, model_text
from coding_study.domain.layout import statement_path
from coding_study.domain.naming import member_name
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import ClassSignature, FunctionSignature, Param, Signature
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeKind,
    NodeType,
    ReturnType,
    Scalar,
    ScalarType,
    VoidType,
)

LINE_LENGTH = 88
"""ruff's default line length."""
INDENT = "    "
SUPPORT_MODULE = "cs_support"
METHOD_BODY = "raise NotImplementedError"
CONSTRUCTOR_BODY = "pass"
"""Constructors never raise, so the first failing operation names an unimplemented method."""
INSTANCE = "self"
SENTENCE_ENDINGS = (".", "?", "!")

_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "int",
    Scalar.LONG: "int",
    Scalar.DOUBLE: "float",
    Scalar.BOOL: "bool",
    Scalar.STRING: "str",
    Scalar.CHAR: "str",
}


class PythonStubGenerator:
    """`StubGenerator` for `python/practice/<snake_slug>.py`."""

    def generate(self, meta: ProblemMeta) -> str:
        preamble = [_header(meta)]
        support_import = _support_import(meta.signature)
        if support_import:
            preamble.append(support_import)
        definition = "\n".join(_definition(meta.signature, _is_async(meta)))
        return "\n\n".join(preamble) + "\n\n\n" + definition + "\n"


def python_type(value_type: ReturnType) -> str:
    match value_type:
        case ScalarType(scalar):
            return _SCALARS[scalar]
        case NodeType(kind):
            return f"{kind} | None"
        case ArrayType(element) | ListType(element):
            return f"list[{python_type(element)}]"
        case VoidType():
            return "None"


@dataclass(frozen=True, slots=True)
class _DefinitionLine:
    """A `def` statement, laid out the way `ruff format` lays it out."""

    indent: str
    name: str
    params: tuple[str, ...]
    returns: str
    is_async: bool = False

    def lines(self) -> list[str]:
        keyword = "async def" if self.is_async else "def"
        opening = f"{self.indent}{keyword} {self.name}("
        closing = f") -> {self.returns}:"
        single_line = f"{opening}{', '.join(self.params)}{closing}"
        if len(single_line) <= LINE_LENGTH:
            return [single_line]
        inner_indent = self.indent + INDENT
        hugged = inner_indent + ", ".join(self.params)
        if len(hugged) <= LINE_LENGTH:
            return [opening, hugged, self.indent + closing]
        exploded = [f"{inner_indent}{param}," for param in self.params]
        return [opening, *exploded, self.indent + closing]


def _header(meta: ProblemMeta) -> str:
    """One line; concurrent problems add a paragraph naming the model."""
    title = meta.title if meta.title.endswith(SENTENCE_ENDINGS) else f"{meta.title}."
    text = f"{title} Statement: {statement_path(meta.slug)}. Run: cstudy test {meta.slug}"
    if meta.concurrency is not None:
        text += f"\n\nConcurrency: {model_text(meta.concurrency, Language.PYTHON)}\n"
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"""{escaped}"""'


def _is_async(meta: ProblemMeta) -> bool:
    """Async model: `blocking` methods are `async def`."""
    concurrency = meta.concurrency
    return concurrency is not None and (
        concurrency.model_for(Language.PYTHON) is ConcurrencyModel.ASYNC
    )


def _support_import(signature: Signature) -> str | None:
    kinds = {kind for value_type in _declared_types(signature) for kind in _node_kinds(value_type)}
    if not kinds:
        return None
    return f"from {SUPPORT_MODULE} import {', '.join(sorted(kinds))}"


def _declared_types(signature: Signature) -> Iterator[ReturnType]:
    if isinstance(signature, FunctionSignature):
        yield from (param.type for param in signature.params)
        yield signature.returns.type
        return
    yield from (param.type for param in signature.constructor_params)
    for method in signature.methods:
        yield from (param.type for param in method.params)
        yield method.returns.type


def _node_kinds(value_type: ReturnType) -> set[NodeKind]:
    match value_type:
        case NodeType(kind):
            return {kind}
        case ArrayType(element) | ListType(element):
            return _node_kinds(element)
        case _:
            return set()


def _definition(signature: Signature, is_async: bool) -> list[str]:
    if isinstance(signature, FunctionSignature):
        return _function(signature)
    return _class(signature, is_async)


def _function(signature: FunctionSignature) -> list[str]:
    definition = _DefinitionLine(
        "",
        _python_name(signature.name),
        _parameters(signature.params),
        python_type(signature.returns.type),
    )
    return [*definition.lines(), INDENT + METHOD_BODY]


def _class(signature: ClassSignature, is_async: bool) -> list[str]:
    constructor = _DefinitionLine(
        INDENT, "__init__", (INSTANCE, *_parameters(signature.constructor_params)), "None"
    )
    lines = [f"class {signature.name}:", *constructor.lines(), INDENT * 2 + CONSTRUCTOR_BODY]
    for method in signature.methods:
        lines.append("")
        if method.level is not None:
            lines.append(f"{INDENT}# Level {method.level}")
        definition = _DefinitionLine(
            INDENT,
            _python_name(method.name),
            (INSTANCE, *_parameters(method.params)),
            python_type(method.returns.type),
            is_async and method.blocking,
        )
        lines += [*definition.lines(), INDENT * 2 + METHOD_BODY]
    return lines


def _parameters(params: tuple[Param, ...]) -> tuple[str, ...]:
    return tuple(f"{_python_name(param.name)}: {python_type(param.type)}" for param in params)


def _python_name(canonical: str) -> str:
    return member_name(canonical, Language.PYTHON)
