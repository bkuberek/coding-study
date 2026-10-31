"""JUnit 5 and kotlin.test files for the levels of a Java or Kotlin project problem
(docs/specs/problem-format.md#generated-test-files).

Each test replays one visible case: it builds the entry class, then turns each call into one
statement in the method's name. A `void` method's call stands alone; any other call is an
assertion with the method's comparator: `assertTrue`, `assertFalse` and `assertNull` for those
values, `assertArrayEquals` (Kotlin: `assertContentEquals`) for arrays, `assertEquals` for the
rest, with a `decimal` compared by its canonical text, since `BigDecimal.equals` compares the
scale too. `unordered` sorts the result and compares it with a literal already sorted as Java sorts
it, and `float` passes the tolerance that the core's comparator allows that value.

The text already matches Google Java style with 4-space indents (Java) and ktlint's official style
(Kotlin), as the stubs do, so no formatter runs. A statement too long for its line breaks its
outermost call's arguments: Java puts them on one continuation line 8 columns deeper, or else one
per line; Kotlin puts each on its own line 4 columns deeper, with a trailing comma and the closing
parenthesis on a line of its own. Arguments that are still too long break the same way.
"""

import re
import textwrap
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from coding_study.adapters.languages.jvm.jvm_types import java_type
from coding_study.adapters.languages.jvm.stubs import INDENT, JAVA_COLUMN_LIMIT, KOTLIN_COLUMN_LIMIT
from coding_study.domain.cases import JsonValue
from coding_study.domain.naming import NameRole, is_reserved, member_name
from coding_study.domain.problem import ComparatorType, Language
from coding_study.domain.project import project_tests_package
from coding_study.domain.project_tests import EDIT_NOTICE, Call, LevelTest, LevelTests
from coding_study.domain.signature import output_type
from coding_study.domain.type_dsl import ArrayType, ListType, Scalar, ScalarType, ValueType

COMMENT = "// "
SENTENCE_ENDINGS = (".", "!", "?")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LEADING_CAPITALS = re.compile(r"[A-Z]+")
_PACKAGE_SEPARATOR = "."
_CODE_SPAN = re.compile(r"`[^`]*`")
_KEPT_SPACE = "\0"
"""Stands in for a space inside a code span while the title wraps."""
_ASSERT_TRUE = "assertTrue"
_ASSERT_FALSE = "assertFalse"
_ASSERT_NULL = "assertNull"
_ASSERT_EQUALS = "assertEquals"
_BIG_DECIMAL = "java.math.BigDecimal"
_LOCAL_DATE = "java.time.LocalDate"
_CANONICAL_DECIMAL = ".stripTrailingZeros().toPlainString()"
"""The runner's text of a `BigDecimal` (docs/specs/runners.md#execution-environment)."""


class JavaTestGenerator:
    """`ProjectTestGenerator` for JUnit 5: `<tests>/Level<n>Test.java`."""

    def generate(self, tests: LevelTests) -> str:
        return _JavaFile(tests).text()


class KotlinTestGenerator:
    """`ProjectTestGenerator` for kotlin.test on JUnit 5: `<tests>/Level<n>Test.kt`."""

    def generate(self, tests: LevelTests) -> str:
        return _KotlinFile(tests).text()


# Expressions, and how a statement lays them out over lines.


@dataclass(frozen=True, slots=True)
class _Atom:
    text: str


@dataclass(frozen=True, slots=True)
class _Call:
    opening: str
    """Up to and including the opening bracket: `assertEquals(`, `List.of(`, `new int[] {`."""
    arguments: tuple["_Expression", ...]
    closing: str = ")"


@dataclass(frozen=True, slots=True)
class _Suffixed:
    expression: "_Expression"
    suffix: str
    """What follows it, such as `.stream().sorted().toList()`."""


type _Expression = _Atom | _Call | _Suffixed


def _flat(expression: _Expression) -> str:
    match expression:
        case _Atom(text):
            return text
        case _Call(opening, arguments, closing):
            return opening + ", ".join(_flat(argument) for argument in arguments) + closing
        case _Suffixed(inner, suffix):
            return _flat(inner) + suffix


@dataclass(frozen=True, slots=True)
class _Printer:
    """Lays out a statement within `column_limit`, breaking calls that do not fit."""

    column_limit: int
    continuation: str
    """The indent of broken arguments, relative to the line their call starts on."""
    arguments_on_one_line: bool
    """Java: every argument on one continuation line, when that fits, before one per line."""
    closing_on_its_own_line: bool
    """Kotlin: a comma after every argument, and the closing bracket on a line of its own."""

    def statement(self, indent: str, prefix: str, expression: _Expression, end: str) -> list[str]:
        """`prefix`, the expression and `end` (`;` in Java), on lines from `indent`."""
        start = indent + prefix
        first, *rest = self._lines(expression, indent, _width(start), end)
        return [start + first, *rest]

    def _lines(self, expression: _Expression, indent: str, column: int, after: str) -> list[str]:
        """The expression from `column` of a line indented by `indent`, then `after`; every line
        but the first carries its own indent."""
        flat = _flat(expression) + after
        if column + _width(flat) <= self.column_limit:
            return [flat]
        match expression:
            case _Suffixed(inner, suffix):
                return self._lines(inner, indent, column, suffix + after)
            case _Call() if expression.arguments:
                return self._broken(expression, indent, after)
            case _:
                return [flat]

    def _broken(self, call: _Call, indent: str, after: str) -> list[str]:
        inner = indent + self.continuation
        if self.arguments_on_one_line:
            listed = ", ".join(_flat(argument) for argument in call.arguments)
            one_line = f"{inner}{listed}{call.closing}{after}"
            if _width(one_line) <= self.column_limit:
                return [call.opening, one_line]
        lines = [call.opening]
        last = len(call.arguments) - 1
        for index, argument in enumerate(call.arguments):
            ends_call = index == last and not self.closing_on_its_own_line
            follows = call.closing + after if ends_call else ","
            first, *rest = self._lines(argument, inner, _width(inner), follows)
            lines += [inner + first, *rest]
        if self.closing_on_its_own_line:
            lines.append(indent + call.closing + after)
        return lines


def _width(text: str) -> int:
    """Columns as editors count them: wide characters take two, combining marks none."""
    return sum(_character_width(character) for character in text)


def _character_width(character: str) -> int:
    if unicodedata.combining(character):
        return 0
    return 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1


@dataclass(frozen=True, slots=True)
class _Escapes:
    """How a language writes characters inside its string and char literals."""

    named: Mapping[str, str]
    control: str
    """A `%` format for any other control character: Java's octal escape, since Java decodes a
    `\\u` escape before it reads the literal, and Kotlin's `\\u`."""

    def string(self, text: str) -> str:
        return '"' + "".join(self._escaped(character, '"') for character in text) + '"'

    def char(self, text: str) -> str:
        return "'" + "".join(self._escaped(character, "'") for character in text) + "'"

    def _escaped(self, character: str, quote: str) -> str:
        if character == quote:
            return f"\\{quote}"
        if character in self.named:
            return self.named[character]
        if unicodedata.category(character) == "Cc":
            return "\\" + self.control % ord(character)
        return character


# A level's file: what the two languages share.


class _LevelFile(ABC):
    language: Language
    printer: _Printer
    escapes: _Escapes
    statement_end: str
    test_class: str
    """`org.junit.jupiter.api.Test` or `kotlin.test.Test`."""
    array_equals: str
    """The assertion that compares two arrays element by element."""

    def __init__(self, tests: LevelTests) -> None:
        self._tests = tests
        self._class_name = tests.signature.name
        self._instance = _instance_name(self._class_name, self.language)
        self._assertions: set[str] = set()
        self._classes: set[str] = set()

    def text(self) -> str:
        tests = [self._test(test) for test in self._tests.tests]
        body = self._class_body([line for test in _separated(tests) for line in test])
        if tests:
            self._classes.add(self.test_class)
        package = self._tests_package()
        entry_package, _, _ = self._tests.entry.rpartition(_PACKAGE_SEPARATOR)
        if entry_package != package:
            self._classes.add(self._tests.entry)
        imports = self._import_lines(sorted(self._assertions), sorted(self._classes))
        lines = [
            *self._header(),
            self._package_line(package),
            "",
            *([*imports, ""] if imports else []),
            *body,
        ]
        return "\n".join(lines) + "\n"

    def _tests_package(self) -> str:
        return project_tests_package(self._tests.project, self.language)

    def _header(self) -> list[str]:
        """The title wraps between words, never inside the command it quotes."""
        width = self.printer.column_limit - len(COMMENT)
        spans = _CODE_SPAN.sub(
            lambda span: span.group().replace(" ", _KEPT_SPACE), self._tests.title
        )
        title = textwrap.wrap(spans, width, break_long_words=False, break_on_hyphens=False)
        return [f"{COMMENT}{line.replace(_KEPT_SPACE, ' ')}" for line in (*title, EDIT_NOTICE)]

    def _class_body(self, members: list[str]) -> list[str]:
        name = self._tests.path.rpartition("/")[2].partition(_PACKAGE_SEPARATOR)[0]
        if not members:
            return [self._empty_class(name)]
        return [f"class {name} {{", *members, "}"]

    def _test(self, test: LevelTest) -> list[str]:
        body = self._construction(test)
        for call in test.calls:
            body += self._statement("", self._call_statement(call))
        notes = _comment_lines(test.note, self.printer.column_limit)
        return [*notes, *self._test_lines(self._test_name(test.case_id), body)]

    def _construction(self, test: LevelTest) -> list[str]:
        """`Bank bank = new Bank(...)`, or the construction alone when no call follows."""
        params = self._tests.signature.constructor_params
        arguments = self._arguments(test.constructor_arguments, [param.type for param in params])
        construction = self._constructor_call(arguments)
        prefix = self._declaration() if test.calls else ""
        return self._statement(prefix, construction)

    def _statement(self, prefix: str, expression: _Expression) -> list[str]:
        return self.printer.statement(INDENT * 2, prefix, expression, self.statement_end)

    def _call_statement(self, call: Call) -> _Expression:
        name = member_name(call.method.name, self.language, NameRole.METHOD)
        types = [param.type for param in call.method.params]
        invocation = _Call(f"{self._instance}.{name}(", self._arguments(call.arguments, types))
        if not call.returns_value:
            return invocation
        return self._assertion(call, invocation)

    def _assertion(self, call: Call, invocation: _Expression) -> _Expression:
        expected, declared = call.expected, output_type(call.method)
        match declared:
            case _ if expected is None:
                return self._assert(_ASSERT_NULL, invocation)
            case ScalarType(Scalar.BOOL) if isinstance(expected, bool):
                return self._assert(_ASSERT_TRUE if expected else _ASSERT_FALSE, invocation)
            case ScalarType(Scalar.DOUBLE) if call.comparator is ComparatorType.FLOAT:
                return self._close_to(expected, invocation)
            case ScalarType(Scalar.DECIMAL) if isinstance(expected, str):
                canonical = _Suffixed(invocation, _CANONICAL_DECIMAL)
                return self._assert(_ASSERT_EQUALS, _Atom(self.escapes.string(expected)), canonical)
            case ArrayType(ScalarType(scalar)) if call.comparator is ComparatorType.UNORDERED:
                in_order = self._value(_java_sorted(expected, scalar), declared)
                sorted_result = self._sorted_array(invocation, scalar)
                return self._assert(self.array_equals, in_order, sorted_result)
            case ArrayType():
                return self._assert(self.array_equals, self._value(expected, declared), invocation)
            case ListType(ScalarType(scalar)) if call.comparator is ComparatorType.UNORDERED:
                in_order = self._value(_java_sorted(expected, scalar), declared)
                return self._assert(_ASSERT_EQUALS, in_order, self._sorted_list(invocation))
            case _:
                return self._assert(_ASSERT_EQUALS, self._value(expected, declared), invocation)

    def _close_to(self, expected: JsonValue, invocation: _Expression) -> _Expression:
        """Passes exactly when the core's comparator does, `abs(a - e) <= tol * max(1, abs(e))`:
        the delta is that product as an expression, `2.5 * 1e-06`, which the JVM computes to the
        same double, where a literal of it would read `2.4999999999999998e-06`."""
        value = float(expected) if isinstance(expected, int | float) else 0.0
        tolerance = repr(float(self._tests.tolerance))
        delta = f"{abs(value)!r} * {tolerance}" if abs(value) > 1 else tolerance
        return self._assert(_ASSERT_EQUALS, _Atom(repr(value)), invocation, _Atom(delta))

    def _assert(self, name: str, *arguments: _Expression) -> _Expression:
        self._assertions.add(name)
        return _Call(f"{name}(", arguments)

    def _arguments(
        self, values: Sequence[JsonValue], types: Sequence[ValueType]
    ) -> tuple[_Expression, ...]:
        """Each value by its parameter's type; a value past the parameters as plain JSON."""
        return tuple(
            self._value(value, types[index] if index < len(types) else None)
            for index, value in enumerate(values)
        )

    def _value(self, value: JsonValue, declared: ValueType | None) -> _Expression:
        if value is None:
            return _Atom("null")
        match declared:
            case ScalarType(scalar):
                return self._scalar(value, scalar)
            case ArrayType() if isinstance(value, list):
                return self._array(value, declared)
            case ListType(element) if isinstance(value, list):
                return self._list(tuple(self._value(item, element) for item in value), value)
            case _:
                return self._plain(value)

    def _scalar(self, value: JsonValue, scalar: Scalar) -> _Expression:
        match scalar:
            case Scalar.INT if isinstance(value, int):
                return _Atom(self._int_literal(value))
            case Scalar.LONG if isinstance(value, int):
                return _Atom(self._long_literal(value))
            case Scalar.DOUBLE if isinstance(value, int | float):
                return _Atom(repr(float(value)))
            case Scalar.CHAR if isinstance(value, str):
                return _Atom(self.escapes.char(value))
            case Scalar.DECIMAL if isinstance(value, str):
                self._classes.add(_BIG_DECIMAL)
                return _Call(self._decimal_constructor(), (_Atom(self.escapes.string(value)),))
            case Scalar.DATE if isinstance(value, str):
                self._classes.add(_LOCAL_DATE)
                return _Call("LocalDate.parse(", (_Atom(self.escapes.string(value)),))
            case _:
                return self._plain(value)

    def _plain(self, value: JsonValue) -> _Expression:
        """A value without a declared type: a JSON scalar as such, an array as a list."""
        match value:
            case bool():
                return _Atom("true" if value else "false")
            case int():
                return _Atom(str(value))
            case float():
                return _Atom(repr(value))
            case str():
                return _Atom(self.escapes.string(value))
            case list():
                return self._list(tuple(self._plain(item) for item in value), value)
            case _:
                raise ValueError(f"no {self.language} literal for {value!r}")

    @abstractmethod
    def _test_name(self, case_id: str) -> str: ...

    @abstractmethod
    def _test_lines(self, name: str, body: list[str]) -> list[str]:
        """From the annotation to the closing brace, indented as a member of the class."""

    @abstractmethod
    def _declaration(self) -> str:
        """What precedes the construction when a call uses the instance: `Bank bank = `."""

    @abstractmethod
    def _constructor_call(self, arguments: tuple[_Expression, ...]) -> _Expression: ...

    @abstractmethod
    def _int_literal(self, value: int) -> str: ...

    @abstractmethod
    def _long_literal(self, value: int) -> str: ...

    @abstractmethod
    def _decimal_constructor(self) -> str: ...

    @abstractmethod
    def _array(self, values: list[JsonValue], declared: ArrayType) -> _Expression: ...

    @abstractmethod
    def _list(self, elements: tuple[_Expression, ...], values: list[JsonValue]) -> _Expression: ...

    @abstractmethod
    def _sorted_list(self, invocation: _Expression) -> _Expression: ...

    @abstractmethod
    def _sorted_array(self, invocation: _Expression, element: Scalar) -> _Expression: ...

    @abstractmethod
    def _package_line(self, package: str) -> str: ...

    @abstractmethod
    def _empty_class(self, name: str) -> str: ...

    @abstractmethod
    def _import_lines(self, assertions: list[str], classes: list[str]) -> list[str]:
        """The import lines, laid out as the language's style orders them."""


class _JavaFile(_LevelFile):
    language = Language.JAVA
    printer = _Printer(JAVA_COLUMN_LIMIT, INDENT * 2, True, False)
    escapes = _Escapes(
        {"\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}, "%03o"
    )
    statement_end = ";"
    test_class = "org.junit.jupiter.api.Test"
    array_equals = "assertArrayEquals"
    _ASSERTIONS = "org.junit.jupiter.api.Assertions"
    _SORTED_OBJECT_ARRAYS: Mapping[Scalar, str] = {
        Scalar.STRING: "String",
        Scalar.DATE: "LocalDate",
    }
    """The class of the array that a stream of these elements sorts back into."""

    def _test_name(self, case_id: str) -> str:
        """The case id with `-` as `_`, since Google Java style allows underscores in JUnit test
        names; `case_` first when that is no identifier or is a keyword."""
        name = case_id.replace("-", "_")
        valid = _IDENTIFIER.fullmatch(name) and not is_reserved(name, Language.JAVA)
        return name if valid else f"case_{name}"

    def _test_lines(self, name: str, body: list[str]) -> list[str]:
        return [f"{INDENT}@Test", f"{INDENT}void {name}() {{", *body, f"{INDENT}}}"]

    def _declaration(self) -> str:
        return f"{self._class_name} {self._instance} = "

    def _constructor_call(self, arguments: tuple[_Expression, ...]) -> _Expression:
        return _Call(f"new {self._class_name}(", arguments)

    def _int_literal(self, value: int) -> str:
        return str(value)

    def _long_literal(self, value: int) -> str:
        return f"{value}L"

    def _decimal_constructor(self) -> str:
        return "new BigDecimal("

    def _array(self, values: list[JsonValue], declared: ArrayType) -> _Expression:
        return _Call(f"new {java_type(declared)} {{", self._initializers(values, declared), "}")

    def _initializers(
        self, values: list[JsonValue], declared: ArrayType
    ) -> tuple[_Expression, ...]:
        """The elements of an array initializer, where an inner array is `{...}` alone."""
        element = declared.element
        if not isinstance(element, ArrayType):
            return tuple(self._value(value, element) for value in values)
        return tuple(
            _Call("{", self._initializers(value, element), "}")
            if isinstance(value, list)
            else _Atom("null")
            for value in values
        )

    def _list(self, elements: tuple[_Expression, ...], values: list[JsonValue]) -> _Expression:
        """`List.of` refuses a `null` element, which `Arrays.asList` takes."""
        if None in values:
            self._classes.add("java.util.Arrays")
            return _Call("Arrays.asList(", elements)
        self._classes.add("java.util.List")
        return _Call("List.of(", elements)

    def _sorted_list(self, invocation: _Expression) -> _Expression:
        return _Suffixed(invocation, ".stream().sorted().toList()")

    def _sorted_array(self, invocation: _Expression, element: Scalar) -> _Expression:
        self._classes.add("java.util.Arrays")
        object_array = self._SORTED_OBJECT_ARRAYS.get(element)
        to_array = f".toArray({object_array}[]::new)" if object_array else ".toArray()"
        return _Suffixed(_Call("Arrays.stream(", (invocation,)), f".sorted(){to_array}")

    def _package_line(self, package: str) -> str:
        return f"package {package};"

    def _empty_class(self, name: str) -> str:
        return f"class {name} {{}}"

    def _import_lines(self, assertions: list[str], classes: list[str]) -> list[str]:
        """Google Java style: the static imports, a blank line, then the others."""
        static = [f"import static {self._ASSERTIONS}.{name};" for name in assertions]
        plain = [f"import {name};" for name in classes]
        return [*static, *([""] if static and plain else []), *plain]


class _KotlinFile(_LevelFile):
    language = Language.KOTLIN
    printer = _Printer(KOTLIN_COLUMN_LIMIT, INDENT, False, True)
    escapes = _Escapes(
        {"\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\r": "\\r", "$": "\\$"}, "u%04X"
    )
    statement_end = ""
    test_class = "kotlin.test.Test"
    array_equals = "assertContentEquals"
    _INT_MIN = -(2**31)
    _LONG_MIN = -(2**63)
    """Kotlin reads `-2147483648` as a `Long`, and has no literal for the smallest `Long`."""
    _ARRAYS: Mapping[Scalar, str] = {
        Scalar.INT: "intArrayOf",
        Scalar.LONG: "longArrayOf",
        Scalar.DOUBLE: "doubleArrayOf",
        Scalar.BOOL: "booleanArrayOf",
        Scalar.CHAR: "charArrayOf",
    }
    _OBJECT_ARRAY = "arrayOf"
    _IMPORTS_LAST = ("java.", "javax.", "kotlin.")
    """ktlint's import layout: every other import, then these, each group in ASCII order."""

    def _test_name(self, case_id: str) -> str:
        """The case id, in backticks when it is no identifier or is a keyword."""
        valid = _IDENTIFIER.fullmatch(case_id) and not is_reserved(case_id, Language.KOTLIN)
        return case_id if valid else f"`{case_id}`"

    def _test_lines(self, name: str, body: list[str]) -> list[str]:
        return [f"{INDENT}@Test", f"{INDENT}fun {name}() {{", *body, f"{INDENT}}}"]

    def _declaration(self) -> str:
        return f"val {self._instance} = "

    def _constructor_call(self, arguments: tuple[_Expression, ...]) -> _Expression:
        return _Call(f"{self._class_name}(", arguments)

    def _int_literal(self, value: int) -> str:
        return "Int.MIN_VALUE" if value == self._INT_MIN else str(value)

    def _long_literal(self, value: int) -> str:
        return "Long.MIN_VALUE" if value == self._LONG_MIN else f"{value}L"

    def _decimal_constructor(self) -> str:
        return "BigDecimal("

    def _array(self, values: list[JsonValue], declared: ArrayType) -> _Expression:
        element = declared.element
        maker = self._OBJECT_ARRAY
        if isinstance(element, ScalarType):
            maker = self._ARRAYS.get(element.scalar, self._OBJECT_ARRAY)
        return _Call(f"{maker}(", tuple(self._value(value, element) for value in values))

    def _list(self, elements: tuple[_Expression, ...], values: list[JsonValue]) -> _Expression:
        return _Call("listOf(", elements)

    def _sorted_list(self, invocation: _Expression) -> _Expression:
        return _Suffixed(invocation, ".sorted()")

    def _sorted_array(self, invocation: _Expression, element: Scalar) -> _Expression:
        return _Suffixed(invocation, ".sortedArray()")

    def _package_line(self, package: str) -> str:
        return f"package {package}"

    def _empty_class(self, name: str) -> str:
        return f"class {name}"

    def _import_lines(self, assertions: list[str], classes: list[str]) -> list[str]:
        names = [*classes, *(f"kotlin.test.{name}" for name in assertions)]
        first = sorted(name for name in names if not name.startswith(self._IMPORTS_LAST))
        groups = [sorted(n for n in names if n.startswith(prefix)) for prefix in self._IMPORTS_LAST]
        return [
            f"import {name}" for name in (*first, *(name for group in groups for name in group))
        ]


def _java_sorted(values: JsonValue, element: Scalar) -> JsonValue:
    """`values` as Java's natural order sorts them: numbers by value, strings by UTF-16 code
    units (`String.compareTo`), dates as their ISO text."""
    if not isinstance(values, list):
        return values
    if element is Scalar.STRING:
        return sorted(values, key=lambda value: str(value).encode("utf-16-be"))
    return sorted(values, key=lambda value: value if isinstance(value, int | float) else str(value))


def _instance_name(class_name: str, language: Language) -> str:
    """The class in lowerCamelCase: `bank` for `Bank`, `lruCache` for `LRUCache`; a keyword gets
    `_` after it."""
    capitals = _LEADING_CAPITALS.match(class_name)
    run = capitals.group() if capitals else ""
    keep = 1 if len(run) > 1 and len(class_name) > len(run) else 0
    lowered = run[: len(run) - keep].lower() + class_name[len(run) - keep :]
    return f"{lowered}_" if is_reserved(lowered, language) else lowered


def _comment_lines(note: str | None, column_limit: int) -> list[str]:
    """A case's note as one sentence of `//` lines above its test."""
    sentence = _sentence(note or "")
    if not sentence:
        return []
    width = column_limit - len(INDENT) - len(COMMENT)
    lines = textwrap.wrap(sentence, width, break_long_words=False, break_on_hyphens=False)
    return [f"{INDENT}{COMMENT}{line}" for line in lines]


def _sentence(note: str) -> str:
    """`note` on one line, starting with a capital and ending like a sentence; empty when blank."""
    text = " ".join(note.split())
    if not text:
        return text
    if text[0].isascii() and text[0].islower():
        text = text[0].upper() + text[1:]
    return text if text.endswith(SENTENCE_ENDINGS) else f"{text}."


def _separated(blocks: list[list[str]]) -> list[list[str]]:
    """Blocks with a blank line before each but the first."""
    return [block if index == 0 else ["", *block] for index, block in enumerate(blocks)]
