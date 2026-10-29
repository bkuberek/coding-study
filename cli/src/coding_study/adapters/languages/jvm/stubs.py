"""Java and Kotlin stub generators (docs/specs/runners.md#stub-generation).

A stub is a header comment, the `practice.<snake_slug>` package, imports, and one class: the
problem's class, or `Solution` for function kinds. Methods throw "Not implemented"; constructors
are empty. Long declarations wrap at the Google Java (100) and ktlint (140) column limits.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from coding_study.adapters.languages.jvm.jvm_types import (
    java_return_type,
    java_type,
    kotlin_return_type,
    kotlin_type,
)
from coding_study.domain.concurrency import model_text
from coding_study.domain.layout import USER_PACKAGE, jvm_class_name, statement_path
from coding_study.domain.naming import NameRole, member_name
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import ClassSignature, Param
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeType,
    ReturnType,
    Scalar,
    ValueType,
    scalars_of,
)

INDENT = "    "
JAVA_COLUMN_LIMIT = 100
KOTLIN_COLUMN_LIMIT = 140
JAVA_NOT_IMPLEMENTED = 'throw new UnsupportedOperationException("Not implemented");'
KOTLIN_NOT_IMPLEMENTED = 'TODO("Not implemented")'
JAVA_IMPORTS = ("import java.util.*;",)
JAVA_CONCURRENCY_IMPORTS = (
    "import java.util.concurrent.*;",
    "import java.util.concurrent.locks.*;",
)
JAVA_INTERRUPTIBLE = " throws InterruptedException"
JAVA_SUPPORT_IMPORT = "import cs.support.*;"
KOTLIN_SUPPORT_IMPORT = "import cs.support.*"
JAVA_SCALAR_IMPORTS = (
    (Scalar.DECIMAL, "import java.math.BigDecimal;"),
    (Scalar.DATE, "import java.time.LocalDate;"),
)
KOTLIN_SCALAR_IMPORTS = (
    (Scalar.DECIMAL, "import java.math.BigDecimal"),
    (Scalar.DATE, "import java.time.LocalDate"),
)
"""Standard library imports of the scalar types that need one, in ASCII order after `cs.support`."""


@dataclass(frozen=True, slots=True)
class _Routine:
    """A function or method, with names already converted for the language."""

    name: str
    params: tuple[tuple[str, ValueType], ...]
    returns: ReturnType
    level: int | None = None
    blocking: bool = False


@dataclass(frozen=True, slots=True)
class _JvmStub:
    """What a Java or Kotlin stub declares, independent of syntax."""

    header: tuple[str, str]
    """The header's two sentences: title and statement path, then the run command."""
    package: str
    class_name: str
    constructor_params: tuple[tuple[str, ValueType], ...] | None
    """None for function kinds, whose `Solution` class keeps the implicit constructor."""
    routines: tuple[_Routine, ...]
    uses_nodes: bool
    scalars: frozenset[Scalar]
    """The scalar types the declarations mention; `decimal` and `date` need an import."""
    concurrency: str | None = None
    """Concurrent problems: the model the header names, e.g. `threads (platform)`."""

    @classmethod
    def of(cls, meta: ProblemMeta, language: Language) -> "_JvmStub":
        signature = meta.signature
        if isinstance(signature, ClassSignature):
            constructor = _named(signature.constructor_params, language)
            routines = tuple(
                _Routine(
                    member_name(method.name, language, NameRole.METHOD),
                    _named(method.params, language),
                    method.returns.type,
                    method.level,
                    method.blocking,
                )
                for method in signature.methods
            )
        else:
            constructor = None
            name = member_name(signature.name, language, NameRole.FUNCTION)
            routines = (_Routine(name, _named(signature.params, language), signature.returns.type),)
        declared_types = [
            *(value_type for _, value_type in constructor or ()),
            *(value_type for routine in routines for _, value_type in routine.params),
            *(routine.returns for routine in routines),
        ]
        return cls(
            header=_header(meta),
            package=f"{USER_PACKAGE}.{meta.snake_slug}",
            class_name=jvm_class_name(meta),
            constructor_params=constructor,
            routines=routines,
            uses_nodes=any(_mentions_node(declared) for declared in declared_types),
            scalars=frozenset(
                scalar for declared in declared_types for scalar in scalars_of(declared)
            ),
            concurrency=(
                model_text(meta.concurrency, language) if meta.concurrency is not None else None
            ),
        )

    def scalar_imports(self, imports: tuple[tuple[Scalar, str], ...]) -> list[str]:
        return [line for scalar, line in imports if scalar in self.scalars]

    def header_lines(self, column_limit: int) -> list[str]:
        concurrency = [] if self.concurrency is None else [f"// Concurrency: {self.concurrency}"]
        return [*_comment_lines(self.header, column_limit), *concurrency]


class JavaStubGenerator:
    """`StubGenerator` for Java: `jvm/java/src/main/java/practice/<snake_slug>/`."""

    def generate(self, meta: ProblemMeta) -> str:
        stub = _JvmStub.of(meta, Language.JAVA)
        support = (JAVA_SUPPORT_IMPORT,) if stub.uses_nodes else ()
        imports = (*support, *stub.scalar_imports(JAVA_SCALAR_IMPORTS), *JAVA_IMPORTS)
        if stub.concurrency is not None:
            imports = (*imports, *JAVA_CONCURRENCY_IMPORTS)
        blocks = [*self._constructor(stub), *(self._method(routine) for routine in stub.routines)]
        lines = [
            *stub.header_lines(JAVA_COLUMN_LIMIT),
            "",
            f"package {stub.package};",
            "",
            *imports,
            "",
            f"public class {stub.class_name} {{",
            *_separated(blocks),
            "}",
        ]
        return _text(lines)

    def _constructor(self, stub: _JvmStub) -> list[list[str]]:
        if stub.constructor_params is None:
            return []
        opening = f"public {stub.class_name}("
        declaration = _java_declaration(opening, _java_params(stub.constructor_params), ") {")
        return [[*declaration, f"{INDENT}}}"]]

    def _method(self, routine: _Routine) -> list[str]:
        opening = f"public {java_return_type(routine.returns)} {routine.name}("
        closing = f"){JAVA_INTERRUPTIBLE} {{" if routine.blocking else ") {"
        return [
            *_level_comment(routine),
            *_java_declaration(opening, _java_params(routine.params), closing),
            f"{INDENT * 2}{JAVA_NOT_IMPLEMENTED}",
            f"{INDENT}}}",
        ]


class KotlinStubGenerator:
    """`StubGenerator` for Kotlin: `jvm/kotlin/src/main/kotlin/practice/<snake_slug>/`."""

    def generate(self, meta: ProblemMeta) -> str:
        stub = _JvmStub.of(meta, Language.KOTLIN)
        support = [KOTLIN_SUPPORT_IMPORT] if stub.uses_nodes else []
        imports = [*support, *stub.scalar_imports(KOTLIN_SCALAR_IMPORTS)]
        if imports:
            imports.append("")
        lines = [
            *stub.header_lines(KOTLIN_COLUMN_LIMIT),
            "",
            f"package {stub.package}",
            "",
            *imports,
            *self._class_header(stub),
            *_separated([self._method(routine) for routine in stub.routines]),
            "}",
        ]
        return _text(lines)

    def _class_header(self, stub: _JvmStub) -> list[str]:
        if not stub.constructor_params:
            return [f"class {stub.class_name} {{"]
        params = _kotlin_params(stub.constructor_params)
        return _kotlin_declaration("", f"class {stub.class_name}(", params, ") {")

    def _method(self, routine: _Routine) -> list[str]:
        return_type = kotlin_return_type(routine.returns)
        closing = ") {" if return_type is None else f"): {return_type} {{"
        params = _kotlin_params(routine.params)
        return [
            *_level_comment(routine),
            *_kotlin_declaration(INDENT, f"fun {routine.name}(", params, closing),
            f"{INDENT * 2}{KOTLIN_NOT_IMPLEMENTED}",
            f"{INDENT}}}",
        ]


def _header(meta: ProblemMeta) -> tuple[str, str]:
    """Title, statement path and run command (docs/specs/runners.md#stub-generation)."""
    return f"{meta.title}. Statement: {statement_path(meta.slug)}.", f"Run: cstudy test {meta.slug}"


def _comment_lines(sentences: tuple[str, ...], column_limit: int) -> list[str]:
    """One `//` line, or one line per sentence when one line would pass the column limit."""
    single_line = f"// {' '.join(sentences)}"
    if len(single_line) <= column_limit:
        return [single_line]
    return [f"// {sentence}" for sentence in sentences]


def _named(params: Iterable[Param], language: Language) -> tuple[tuple[str, ValueType], ...]:
    return tuple(
        (member_name(param.name, language, NameRole.PARAMETER), param.type) for param in params
    )


def _mentions_node(declared_type: ReturnType) -> bool:
    match declared_type:
        case NodeType():
            return True
        case ArrayType(element) | ListType(element):
            return _mentions_node(element)
        case _:
            return False


def _java_params(params: Sequence[tuple[str, ValueType]]) -> list[str]:
    return [f"{java_type(value_type)} {name}" for name, value_type in params]


def _kotlin_params(params: Sequence[tuple[str, ValueType]]) -> list[str]:
    return [f"{name}: {kotlin_type(value_type)}" for name, value_type in params]


def _java_declaration(opening: str, params: list[str], closing: str) -> list[str]:
    """One line, or Google Java style: one parameter per line with a +8 continuation indent."""
    single_line = f"{INDENT}{opening}{', '.join(params)}{closing}"
    if len(single_line) <= JAVA_COLUMN_LIMIT:
        return [single_line]
    continuation = INDENT * 3
    wrapped = [f"{continuation}{param}," for param in params[:-1]]
    return [f"{INDENT}{opening}", *wrapped, f"{continuation}{params[-1]}{closing}"]


def _kotlin_declaration(indent: str, opening: str, params: list[str], closing: str) -> list[str]:
    """One line, or ktlint style: one parameter per line, trailing comma, closing on its own."""
    single_line = f"{indent}{opening}{', '.join(params)}{closing}"
    if len(single_line) <= KOTLIN_COLUMN_LIMIT:
        return [single_line]
    wrapped = [f"{indent}{INDENT}{param}," for param in params]
    return [f"{indent}{opening}", *wrapped, f"{indent}{closing}"]


def _level_comment(routine: _Routine) -> list[str]:
    return [] if routine.level is None else [f"{INDENT}// Level {routine.level}"]


def _separated(blocks: list[list[str]]) -> list[str]:
    """Blocks of lines with one blank line between consecutive blocks."""
    lines: list[str] = []
    for index, block in enumerate(blocks):
        if index:
            lines.append("")
        lines.extend(block)
    return lines


def _text(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"
