"""pytest files for the levels of a Python project problem
(docs/specs/problem-format.md#generated-test-files).

Each test replays one visible case: it builds the entry class, then turns each call into one
statement in the method's Python name. A `void` method's call stands alone; any other call is an
assertion with the method's comparator: `is` for `True`, `False` and `None` and `==` for any other
`exact` value, `sorted(...)` against a sorted literal for `unordered`, and `pytest.approx` for
`float`. Values are Python literals, with `Decimal("2.50")` and `date.fromisoformat("2026-01-01")`
for `decimal` and `date`, imported when used; a whole decimal is `Decimal(10)`, since ruff's
default rules (FURB157) flag `Decimal("10")`.

The text already matches `ruff format` with its default line length, so no formatter runs. A
statement too long for one line is laid out by the printer of test_printer.py, of the same family
as ruff's: each pair of brackets is a group that keeps its content on one line when it fits, and
otherwise moves it to indented lines of its own, one item per line, with a trailing comma after
several items. Call arguments get a second chance on a single indented line first. An assertion
is wrapped in parentheses, broken before its operator, unless its right side ends with brackets of
its own.
"""

import keyword
import re
import textwrap
import unicodedata
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from coding_study.adapters.languages.python.stub_generator import (
    INDENT,
    LINE_LENGTH,
    SENTENCE_ENDINGS,
)
from coding_study.adapters.languages.test_printer import (
    SOFT_LINE,
    SPACE_OR_LINE,
    Doc,
    Group,
    IfBreak,
    Indent,
    Style,
    Text,
    flattened,
    layout,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.naming import NameRole, member_name, snake_case
from coding_study.domain.problem import ComparatorType, Language
from coding_study.domain.project_tests import EDIT_NOTICE, Call, LevelTest, LevelTests
from coding_study.domain.signature import output_type
from coding_study.domain.type_dsl import ArrayType, ListType, Scalar, ScalarType, ValueType

DATE_IMPORT = "from datetime import date"
DECIMAL_IMPORT = "from decimal import Decimal"
PYTEST_IMPORT = "import pytest"
_STANDARD_LIBRARY_IMPORTS = (DATE_IMPORT, DECIMAL_IMPORT)
"""In isort order: sorted by module."""
_NAMES_IN_TESTS = frozenset({*keyword.kwlist, "sorted", "pytest", "date"})
"""What the instance may not be called: keywords, and the names a test body uses."""
_QUOTE = '"'
_ALTERNATE_QUOTE = "'"
_DOCSTRING_QUOTES = '"""'
_ESCAPES = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_WHOLE_NUMBER = re.compile(r"-?[0-9]+")
_NEGATIVE_ZERO = "-0"


def _call(callee: str, arguments: Sequence[Doc]) -> Doc:
    """`callee(...)`: the arguments on one line, else on one indented line, else one per line."""
    if not arguments:
        return Text(f"{callee}()")
    inner = Group(_comma_separated(arguments))
    return (Text(f"{callee}("), Group((Indent((SOFT_LINE, inner)), SOFT_LINE)), Text(")"))


def _list(items: Sequence[Doc]) -> Doc:
    """`[...]`: the items on one line, else one per line."""
    if not items:
        return Text("[]")
    content = (Indent((SOFT_LINE, _comma_separated(items))), SOFT_LINE)
    return (Text("["), Group(content), Text("]"))


def _comma_separated(items: Sequence[Doc]) -> Doc:
    separated: list[Doc] = []
    for index, item in enumerate(items):
        if index:
            separated += [Text(","), SPACE_OR_LINE]
        separated.append(item)
    if len(items) > 1:
        separated.append(IfBreak(Text(",")))
    return tuple(separated)


def _assertion(left: Doc, operator: str, right: Doc) -> Doc:
    """`assert left <operator> right`, parenthesized and broken before the operator when it is
    too long, unless the right side can break its own brackets instead."""
    plain = (Text("assert "), left, Text(f" {operator} "), right)
    if _breaks_own_brackets(plain, right):
        return plain
    comparison = Group((left, SPACE_OR_LINE, Text(f"{operator} "), right))
    return (Text("assert "), _parenthesized(comparison))


def _assignment(name: str, value: Doc) -> Doc:
    """`name = value`, with the value parenthesized when it is too long and cannot break its own
    brackets: `Cls()` has none to break."""
    plain = (Text(f"{name} = "), value)
    if _breaks_own_brackets(plain, value):
        return plain
    return (Text(f"{name} = "), _parenthesized(value))


def _breaks_own_brackets(statement: Doc, last: Doc) -> bool:
    """Whether `statement` breaks the brackets of its `last` part, and those before it, instead of
    adding parentheses: `last` has brackets with something in them, and the line fits up to the
    first bracket of the statement."""
    return _has_group(last) and len(INDENT) + _width_before_group(statement) <= LINE_LENGTH


def _parenthesized(doc: Doc) -> Doc:
    """`doc` in parentheses of its own, on indented lines, when it does not fit on one line."""
    return Group((IfBreak(Text("(")), Indent((SOFT_LINE, doc)), SOFT_LINE, IfBreak(Text(")"))))


def _has_group(doc: Doc) -> bool:
    match doc:
        case Group():
            return True
        case tuple():
            return any(_has_group(part) for part in doc)
        case Indent(content):
            return _has_group(content)
        case _:
            return False


def _width_before_group(doc: Doc) -> int:
    """The columns of the text before the first group of `doc`."""
    width = 0
    for part in flattened(doc):
        if isinstance(part, Group):
            break
        if isinstance(part, Text):
            width += _width(part.text)
    return width


class PythonTestGenerator:
    """`ProjectTestGenerator` for pytest: `<tests>/test_level_<n>.py`."""

    def generate(self, tests: LevelTests) -> str:
        return _LevelFile(tests).text()


class _LevelFile:
    def __init__(self, tests: LevelTests) -> None:
        self._tests = tests
        self._instance = _instance_name(tests.signature.name)
        self._values = _Values(tests.tolerance)

    def text(self) -> str:
        functions = [self._function(test) for test in self._tests.tests]
        header = _module_docstring(self._tests.title)
        if not functions:
            return f"{header}\n"
        blocks = [f"{header}\n\n{self._imports()}", *functions]
        return "\n\n\n".join(blocks) + "\n"

    def _imports(self) -> str:
        used = self._values.imports
        blocks = [
            "\n".join(line for line in _STANDARD_LIBRARY_IMPORTS if line in used),
            PYTEST_IMPORT if PYTEST_IMPORT in used else "",
            f"from {self._tests.entry} import {self._tests.signature.name}",
        ]
        return "\n\n".join(block for block in blocks if block)

    def _function(self, test: LevelTest) -> str:
        lines = [f"def test_{test.case_id.replace('-', '_')}() -> None:"]
        lines += _docstring(test.note or "")
        lines.append(layout(self._construction(test), _STYLE, INDENT))
        lines += (layout(self._statement(call), _STYLE, INDENT) for call in test.calls)
        return "\n".join(lines)

    def _construction(self, test: LevelTest) -> Doc:
        """`bank = Bank(...)`, or `Bank(...)` alone when no call follows to use the instance."""
        params = self._tests.signature.constructor_params
        types = [param.type for param in params]
        arguments = self._values.arguments(test.constructor_arguments, types)
        construction = _call(self._tests.signature.name, arguments)
        return _assignment(self._instance, construction) if test.calls else construction

    def _statement(self, call: Call) -> Doc:
        name = member_name(call.method.name, Language.PYTHON, NameRole.METHOD)
        types = [param.type for param in call.method.params]
        invocation = _call(
            f"{self._instance}.{name}", self._values.arguments(call.arguments, types)
        )
        if not call.returns_value:
            return invocation
        expected, declared = call.expected, output_type(call.method)
        if call.comparator is ComparatorType.FLOAT and _holds_numbers(expected):
            return _assertion(invocation, "==", self._values.close_to(expected, declared))
        if call.comparator is ComparatorType.UNORDERED and isinstance(expected, list):
            in_order = self._values.in_python_order(expected, declared)
            return _assertion(_call("sorted", [invocation]), "==", in_order)
        if expected is None or isinstance(expected, bool):
            return _assertion(invocation, "is", Text(_literal(expected)))
        return _assertion(invocation, "==", self._values.doc(expected, declared))


class _Values:
    """Python expressions for JSON values, and the imports they need."""

    def __init__(self, tolerance: float) -> None:
        self._tolerance = _literal(float(tolerance))
        self.imports: set[str] = set()

    def doc(self, value: JsonValue, declared: ValueType | None) -> Doc:
        match declared:
            case ScalarType(Scalar.DECIMAL) if isinstance(value, str):
                self.imports.add(DECIMAL_IMPORT)
                return _call("Decimal", [Text(_decimal_argument(value))])
            case ScalarType(Scalar.DATE) if isinstance(value, str):
                self.imports.add(DATE_IMPORT)
                return _call("date.fromisoformat", [Text(_literal(value))])
            case _ if isinstance(value, list):
                element = _element_type(declared)
                return _list([self.doc(item, element) for item in value])
            case _:
                return Text(_literal(value))

    def arguments(self, values: Sequence[JsonValue], types: Sequence[ValueType]) -> list[Doc]:
        """Each value by its parameter's type; values past the parameters as plain JSON."""
        return [
            self.doc(value, types[index] if index < len(types) else None)
            for index, value in enumerate(values)
        ]

    def in_python_order(self, values: list[JsonValue], declared: ValueType | None) -> Doc:
        """The list as `sorted` orders it in Python: decimals by value, the rest as they are."""
        element = _element_type(declared)
        ordered = sorted(values, key=lambda value: _sort_key(value, element))
        return self.doc(ordered, declared)

    def close_to(self, value: JsonValue, declared: ValueType | None) -> Doc:
        """`pytest.approx` around each number or innermost list of numbers in `value`."""
        if isinstance(value, list) and not all(_is_number(item) for item in value):
            element = _element_type(declared)
            return _list([self._close_to_item(item, element) for item in value])
        self.imports.add(PYTEST_IMPORT)
        tolerance = [Text(f"rel={self._tolerance}"), Text(f"abs={self._tolerance}")]
        return _call("pytest.approx", [self.doc(value, declared), *tolerance])

    def _close_to_item(self, value: JsonValue, declared: ValueType | None) -> Doc:
        return (
            self.close_to(value, declared) if _holds_numbers(value) else self.doc(value, declared)
        )


def _element_type(declared: ValueType | None) -> ValueType | None:
    match declared:
        case ArrayType(element) | ListType(element):
            return element
        case _:
            return None


def _sort_key(value: JsonValue, declared: ValueType | None) -> Any:
    """What `sorted` compares in Python: a decimal's value, other values as they are."""
    match declared:
        case ScalarType(Scalar.DECIMAL) if isinstance(value, str):
            return Decimal(value)
        case _ if isinstance(value, list):
            element = _element_type(declared)
            return [_sort_key(item, element) for item in value]
        case _:
            return value


def _is_number(value: JsonValue) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _holds_numbers(value: JsonValue) -> bool:
    if isinstance(value, list):
        return any(_holds_numbers(item) for item in value)
    return _is_number(value)


def _literal(value: JsonValue) -> str:
    match value:
        case None | bool() | int() | float():
            return repr(value)
        case str():
            return _string_literal(value)
        case _:
            raise ValueError(f"no Python literal for {value!r}")


def _decimal_argument(text: str) -> str:
    """The text, except that a whole number is an int, which ruff's FURB157 asks for: `Decimal(10)`.
    `-0` keeps its text, since `Decimal(-0)` would lose the sign."""
    whole = _WHOLE_NUMBER.fullmatch(text) and text != _NEGATIVE_ZERO
    return str(int(text)) if whole else _string_literal(text)


def _string_literal(text: str) -> str:
    """Double quotes unless the text holds more double than single quotes, as ruff prefers."""
    quote = _ALTERNATE_QUOTE if text.count(_QUOTE) > text.count(_ALTERNATE_QUOTE) else _QUOTE
    return quote + "".join(_escaped(character, quote) for character in text) + quote


def _escaped(character: str, quote: str) -> str:
    if character == quote:
        return f"\\{character}"
    if character in _ESCAPES:
        return _ESCAPES[character]
    return character if character.isprintable() else repr(character)[1:-1]


def _instance_name(class_name: str) -> str:
    """The class in snake_case: `bank` for `Bank`, `lru_cache` for `LRUCache`."""
    name = snake_case(class_name)
    return f"{name}_" if name in _NAMES_IN_TESTS else name


def _module_docstring(title: str) -> str:
    opening = textwrap.wrap(
        _DOCSTRING_QUOTES + title,
        width=LINE_LENGTH,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return "\n".join([*opening, "", EDIT_NOTICE, _DOCSTRING_QUOTES])


def _docstring(note: str) -> list[str]:
    """A test's note as a sentence. Too long for one line, it wraps within the line length and
    its closing quotes take a line of their own. ruff keeps the closing quotes of a one-line
    docstring on its line, so a note that only they push past the length wraps earlier."""
    sentence = _sentence(note)
    if not sentence:
        return []
    text = _docstring_text(sentence)
    single = f"{INDENT}{_DOCSTRING_QUOTES}{text}{_DOCSTRING_QUOTES}"
    if _width(single) <= LINE_LENGTH:
        return [single]
    for width in (LINE_LENGTH, LINE_LENGTH - len(_DOCSTRING_QUOTES)):
        wrapped = textwrap.wrap(
            text,
            width=width,
            initial_indent=INDENT + _DOCSTRING_QUOTES,
            subsequent_indent=INDENT,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if len(wrapped) > 1:
            return [*wrapped, INDENT + _DOCSTRING_QUOTES]
    return [single]


def _sentence(note: str) -> str:
    """`note` on one line, starting with a capital and ending like a sentence; empty when blank."""
    text = " ".join(note.split())
    if not text:
        return text
    if text[0].isascii() and text[0].islower():
        text = text[0].upper() + text[1:]
    return text if text.endswith(SENTENCE_ENDINGS) else f"{text}."


def _docstring_text(sentence: str) -> str:
    """`sentence` as docstring source: backslashes kept, no closing quotes inside it, and a space
    before a leading quote, which ruff adds."""
    text = sentence.replace("\\", "\\\\").replace(_DOCSTRING_QUOTES, '""\\"')
    return f" {text}" if text.startswith(_QUOTE) else text


def _width(text: str) -> int:
    """Columns as ruff counts them: wide characters take two, combining marks none."""
    return sum(_character_width(character) for character in text)


def _character_width(character: str) -> int:
    if unicodedata.combining(character):
        return 0
    return 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1


_STYLE = Style(LINE_LENGTH, INDENT, _width)
"""How ruff lays out a statement: its line length, indentation and column count."""
