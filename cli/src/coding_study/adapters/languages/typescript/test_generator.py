"""`node:test` files for the levels of a TypeScript project problem
(docs/specs/problem-format.md#generated-test-files).

Each test replays one visible case: it builds the entry class, then turns each call into one
statement. A `void` method's call stands alone; any other call is an assertion with the method's
comparator, from `node:assert/strict`: `assert.equal` for an `exact` scalar and `assert.deepEqual`
for an `exact` list; for `unordered`, a sorted copy against a literal already sorted as JavaScript's
default sort orders it, by the UTF-16 code units of each item's text (`[10, 100, 9]`); for
`float`, the helper `assertClose`, defined once in the file when used, which holds exactly when
`abs(a - e) <= tol * max(1, abs(e))`, item by item through lists, and compares anything else
strictly, as the core does. Values are JavaScript literals: a `date` is its ISO string, which is
how a project declares it, since a project folder cannot import the runner's `IsoDate`; no
TypeScript project holds a `decimal` (`cstudy verify` S14).

A generated test passes when the core comparator would pass the case and fails when it would fail
it, with two exceptions. Strict assertions compare numbers with `Object.is`, so a result of `-0`
fails against `0`, where the core sees `0`, since JSON has no negative zero. And the default sort
leaves items with the same text in the order it found them, so an `unordered` list of lists whose
different items join to the same text (`["a,b"]` and `["a", "b"]`) can fail.

The text already matches Prettier 3 with its default options (80 columns, two-space indentation,
double quotes, trailing commas everywhere), so no formatter runs. Statements are documents built as
Prettier's printer for JavaScript builds them for the few constructs a test uses, laid out by the
printer of test_printer.py: call arguments break one per line, except that a last argument that is
a list breaks on its own when the rest of the call fits before it; a list of numbers fills its
lines; a list of several lists of several items always breaks; a declaration breaks after `=`
when the construction does not fit up to its first bracket.
"""

import posixpath
import textwrap
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from coding_study.adapters.languages.test_printer import (
    SOFT_LINE,
    SPACE_OR_LINE,
    BreakParent,
    Doc,
    Fill,
    Group,
    GroupId,
    IfBreak,
    Indent,
    Style,
    Text,
    layout,
    will_break,
)
from coding_study.adapters.languages.typescript.stub_generator import INDENT, PRINT_WIDTH
from coding_study.domain.cases import JsonValue
from coding_study.domain.naming import RESERVED_WORDS, NameRole, member_name, snake_case
from coding_study.domain.problem import ComparatorType, Language
from coding_study.domain.project import PATH_SEPARATOR, Project
from coding_study.domain.project_tests import EDIT_NOTICE, Call, LevelTest, LevelTests

ASSERT_IMPORT = 'import assert from "node:assert/strict";'
TEST_IMPORT = 'import { test } from "node:test";'
ASSERT_CLOSE = "assertClose"
ASSERT_CLOSE_FUNCTION = """\
function assertClose(actual: unknown, expected: unknown, tolerance: number) {
  if (Array.isArray(actual) && Array.isArray(expected)) {
    assert.equal(actual.length, expected.length);
    for (const [index, item] of expected.entries()) {
      assertClose(actual[index], item, tolerance);
    }
  } else if (typeof actual === "number" && typeof expected === "number") {
    const bound = tolerance * Math.max(1, Math.abs(expected));
    assert.ok(
      Math.abs(actual - expected) <= bound,
      `${actual} is not within ${bound} of ${expected}`,
    );
  } else {
    assert.deepEqual(actual, expected);
  }
}"""
"""The `float` comparator of the core, in TypeScript."""
COMMENT = "// "
_NAMES_IN_TESTS = RESERVED_WORDS[Language.TYPESCRIPT] | {
    "arguments",
    "eval",
    "undefined",
    "assert",
    "test",
    ASSERT_CLOSE,
}
"""What the instance may not be called: reserved words, and the names a test body uses."""
_PARENT_DIRECTORY = f"..{PATH_SEPARATOR}"
_CURRENT_DIRECTORY = f".{PATH_SEPARATOR}"
_QUOTE = '"'
_ALTERNATE_QUOTE = "'"
_ESCAPES = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_LAST_BYTE_ESCAPE = 0xFF
_LAST_CODE_UNIT_ESCAPE = 0xFFFF
_PLAIN_NOTATION_DIGITS = 21
"""JavaScript writes a number without an exponent below 10^21, and down to 10^-6."""
_PLAIN_NOTATION_LEADING_ZEROS = 6
_UNSIGNED_EXPONENT = "e+"
"""Prettier writes `1e21` where JavaScript writes `1e+21`."""
_INVISIBLE = (range(0, 32), range(127, 160), range(768, 880), range(65024, 65040))
"""Prettier gives control characters, combining marks and variation selectors no width."""
_WIDE = ("W", "F")


class TypeScriptTestGenerator:
    """`ProjectTestGenerator` for `node:test`: `<tests>/level-<n>.test.ts`."""

    def generate(self, tests: LevelTests) -> str:
        return _LevelFile(tests).text()


class _LevelFile:
    def __init__(self, tests: LevelTests) -> None:
        self._tests = tests
        self._instance = _instance_name(tests.signature.name)
        self._tolerance = _number(tests.tolerance)
        self._asserts = False
        self._compares_floats = False

    def text(self) -> str:
        header = [*_comment(self._tests.title), *_comment(EDIT_NOTICE)]
        if not self._tests.tests:
            return "\n".join(header) + "\n"
        tests = [self._test(test) for test in self._tests.tests]
        imports = [ASSERT_IMPORT] if self._asserts else []
        entry = _entry_path(self._tests.project)
        blocks = [
            "\n".join([*header, *imports, TEST_IMPORT]),
            f'import {{ {self._tests.signature.name} }} from "{entry}";',
            *([ASSERT_CLOSE_FUNCTION] if self._compares_floats else []),
            *tests,
        ]
        return "\n\n".join(blocks) + "\n"

    def _test(self, test: LevelTest) -> str:
        lines = [*_comment(test.note or ""), f"test({_string(test.case_id)}, () => {{"]
        lines.append(layout(self._construction(test), _STYLE, INDENT))
        lines += (layout(self._statement(call), _STYLE, INDENT) for call in test.calls)
        return "\n".join([*lines, "});"])

    def _construction(self, test: LevelTest) -> Doc:
        """`const bank = new Bank(...);`, or `new Bank(...);` alone when no call follows to use
        the instance."""
        arguments = [_value(value) for value in test.constructor_arguments]
        construction = (Text(f"new {self._tests.signature.name}"), _arguments(arguments))
        if not test.calls:
            return (construction, Text(";"))
        return _declaration(self._instance, construction)

    def _statement(self, call: Call) -> Doc:
        name = member_name(call.method.name, Language.TYPESCRIPT, NameRole.METHOD)
        arguments = [_value(value) for value in call.arguments]
        invocation = _member_call(Text(f"{self._instance}.{name}"), arguments)
        if not call.returns_value:
            return (invocation, Text(";"))
        expected = call.expected
        if call.comparator is ComparatorType.FLOAT and _holds_numbers(expected):
            self._compares_floats = self._asserts = True
            tolerance = _Expression(Text(self._tolerance), _Kind.NUMBER)
            compared = [_Expression(invocation), _value(expected), tolerance]
            return (Text(ASSERT_CLOSE), _arguments(compared), Text(";"))
        self._asserts = True
        if call.comparator is ComparatorType.UNORDERED and isinstance(expected, list):
            spread = _array([_Expression((Text("..."), invocation))])
            sorted_copy = _member_call((spread.doc, Text(".sort")), [])
            in_order = sorted(expected, key=_sort_key)
            return _assertion("assert.deepEqual", sorted_copy, _value(in_order))
        if isinstance(expected, list):
            return _assertion("assert.deepEqual", invocation, _value(expected))
        return _assertion("assert.equal", invocation, _value(expected))


# Expressions, built as Prettier's printer for JavaScript builds them.


class _Kind(Enum):
    """What Prettier's layout of an expression depends on."""

    NUMBER = auto()
    """A number literal, maybe negative."""
    ARRAY = auto()
    OTHER = auto()


@dataclass(frozen=True, slots=True)
class _Expression:
    doc: Doc
    kind: _Kind = _Kind.OTHER
    items: tuple["_Expression", ...] = ()
    """An array's elements."""

    @property
    def is_number_array(self) -> bool:
        """Prettier fills the lines of an array of numbers ("concisely printed")."""
        numbers = all(item.kind is _Kind.NUMBER for item in self.items)
        return self.kind is _Kind.ARRAY and bool(self.items) and numbers

    @property
    def can_expand(self) -> bool:
        """An array with elements, which a call can break on its own as its last argument."""
        return self.kind is _Kind.ARRAY and bool(self.items)


def _value(value: JsonValue) -> _Expression:
    match value:
        case None:
            return _Expression(Text("null"))
        case bool():
            return _Expression(Text("true" if value else "false"))
        case int() | float():
            return _Expression(Text(_number(value)), _Kind.NUMBER)
        case str():
            return _Expression(Text(_string(value)))
        case list():
            return _array([_value(item) for item in value])
        case _:
            raise ValueError(f"no TypeScript literal for {value!r}")


def _array(items: Sequence[_Expression]) -> _Expression:
    """`[...]`: on one line, else one item per line, or filled lines for numbers; a list of
    several lists of several items always breaks."""
    if not items:
        return _Expression(Text("[]"), _Kind.ARRAY)
    array = _Expression(Text("[]"), _Kind.ARRAY, tuple(items))
    named = GroupId()
    if array.is_number_array:
        content: Doc = _filled(items, IfBreak(Text(","), group=named))
    else:
        content = (_separated(items), IfBreak(Text(",")))
    nested = len(items) > 1 and all(
        item.kind is _Kind.ARRAY and len(item.items) > 1 for item in items
    )
    brackets = (Text("["), Indent((SOFT_LINE, content)), SOFT_LINE, Text("]"))
    return _Expression(Group(brackets, breaks=nested, id=named), _Kind.ARRAY, tuple(items))


def _separated(items: Sequence[_Expression]) -> Doc:
    parts: list[Doc] = []
    for index, item in enumerate(items):
        parts += [Text(","), SPACE_OR_LINE] if index else []
        parts.append(Group(item.doc))
    return tuple(parts)


def _filled(items: Sequence[_Expression], trailing_comma: Doc) -> Doc:
    *others, last = items
    parts: list[Doc] = []
    for item in others:
        parts += [(item.doc, Text(",")), SPACE_OR_LINE]
    parts.append((last.doc, trailing_comma))
    return Fill(tuple(parts))


def _arguments(arguments: Sequence[_Expression]) -> Doc:
    """`(...)`: on one line, else one argument per line with a trailing comma. A last argument
    that is an array breaks on its own first, unless the argument before it is an array too or it
    holds numbers only."""
    if not arguments:
        return Text("()")
    *others, last = arguments
    leading: list[Doc] = [(argument.doc, Text(","), SPACE_OR_LINE) for argument in others]
    printed = [*leading, last.doc]
    broken_out = Group(
        (Text("("), Indent((SPACE_OR_LINE, *printed, Text(","))), SPACE_OR_LINE, Text(")")),
        breaks=True,
    )
    if not _breaks_last_first(arguments):
        contents = (Text("("), Indent((SOFT_LINE, *printed)), IfBreak(Text(",")), SOFT_LINE)
        return Group((*contents, Text(")")), breaks=any(will_break(doc) for doc in printed))
    if any(will_break(doc) for doc in leading):
        return broken_out
    last_broken = (Text("("), *leading, Group(last.doc, breaks=True), Text(")"))
    if will_break(last.doc):
        return (BreakParent(), Group(last_broken, alternatives=(broken_out,)))
    flat = (Text("("), *leading, last.doc, Text(")"))
    return Group(flat, alternatives=(last_broken, broken_out))


def _breaks_last_first(arguments: Sequence[_Expression]) -> bool:
    """Prettier's `shouldGroupLast`, for the arguments a test passes."""
    last = arguments[-1]
    before = arguments[-2] if len(arguments) > 1 else None
    after_an_array = before is not None and before.kind is _Kind.ARRAY
    numbers_after_others = len(arguments) > 1 and last.is_number_array
    return last.can_expand and not after_an_array and not numbers_after_others


def _member_call(callee: Doc, arguments: Sequence[_Expression]) -> Doc:
    """`object.method(...)`, a member chain short enough to stay on one line up to its call."""
    return Group((callee, _arguments(arguments)))


def _assertion(function: str, actual: Doc, expected: _Expression) -> Doc:
    """`assert.<function>(actual, expected);`."""
    return (_member_call(Text(function), [_Expression(actual), expected]), Text(";"))


def _declaration(name: str, value: Doc) -> Doc:
    """`const name = value;`, broken after `=` only when the value does not fit up to where it
    can break (Prettier's "fluid" assignment)."""
    after_equals = GroupId()
    declarator = (
        Group(Text(name)),
        Text(" ="),
        Group(Indent(SPACE_OR_LINE), id=after_equals),
        IfBreak(Indent(value), value, after_equals),
    )
    return Group((Text("const "), Group(declarator), Text(";")))


# Literals


def _number(value: float) -> str:
    """The number as JavaScript writes it (`String(value)`), as Prettier prints it."""
    return _javascript_text(value).replace(_UNSIGNED_EXPONENT, "e")


def _javascript_text(value: JsonValue) -> str:
    """`String(value)` in JavaScript, which its default sort compares."""
    match value:
        case None:
            return "null"
        case bool():
            return "true" if value else "false"
        case int() | float():
            return _javascript_number(value)
        case str():
            return value
        case list():
            return ",".join("" if item is None else _javascript_text(item) for item in value)
        case _:
            raise ValueError(f"no JavaScript text for {value!r}")


def _javascript_number(value: float) -> str:
    """The shortest digits that read back as `value`, in plain notation from 10^-6 to below
    10^21 and with an exponent outside (`1e-7`, `1e+21`): ECMAScript's Number::toString."""
    if value == 0:
        return "0"
    digits, point = _shortest_digits(abs(value))
    sign = "-" if value < 0 else ""
    count = len(digits)
    if count <= point <= _PLAIN_NOTATION_DIGITS:
        return f"{sign}{digits}{'0' * (point - count)}"
    if 0 < point <= _PLAIN_NOTATION_DIGITS:
        return f"{sign}{digits[:point]}.{digits[point:]}"
    if -_PLAIN_NOTATION_LEADING_ZEROS < point <= 0:
        return f"{sign}0.{'0' * -point}{digits}"
    exponent = point - 1
    mantissa = digits if count == 1 else f"{digits[0]}.{digits[1:]}"
    return f"{sign}{mantissa}e{'+' if exponent >= 0 else '-'}{abs(exponent)}"


def _shortest_digits(magnitude: float) -> tuple[str, int]:
    """The significant digits of a positive number, and how many of them come before its point
    (negative for leading zeros after it): `("15", 1)` for 1.5, `("1", -6)` for 1e-7."""
    mantissa, _, exponent = repr(magnitude).partition("e")
    whole, _, fraction = mantissa.partition(".")
    figures = whole + fraction
    leading_zeros = len(figures) - len(figures.lstrip("0"))
    point = len(whole) + int(exponent or 0) - leading_zeros
    return figures.strip("0"), point


def _string(text: str) -> str:
    """Double quotes unless the text holds more double than single quotes, as Prettier
    prefers; control and other unprintable characters escaped."""
    quote = _ALTERNATE_QUOTE if text.count(_QUOTE) > text.count(_ALTERNATE_QUOTE) else _QUOTE
    return quote + "".join(_escaped(character, quote) for character in text) + quote


def _escaped(character: str, quote: str) -> str:
    if character == quote:
        return f"\\{character}"
    if character in _ESCAPES:
        return _ESCAPES[character]
    if character.isprintable():
        return character
    code = ord(character)
    if code <= _LAST_BYTE_ESCAPE:
        return f"\\x{code:02x}"
    if code <= _LAST_CODE_UNIT_ESCAPE:
        return f"\\u{code:04x}"
    return f"\\u{{{code:x}}}"


def _sort_key(value: JsonValue) -> bytes:
    """What JavaScript's default sort compares: the UTF-16 code units of the value's text."""
    return _javascript_text(value).encode("utf-16-be", "surrogatepass")


def _holds_numbers(value: JsonValue) -> bool:
    if isinstance(value, list):
        return any(_holds_numbers(item) for item in value)
    return isinstance(value, int | float) and not isinstance(value, bool)


# Names, paths and comments


def _instance_name(class_name: str) -> str:
    """The class in camelCase: `bank` for `Bank`, `lruCache` for `LRUCache`."""
    first, *others = snake_case(class_name).split("_")
    name = first + "".join(word.capitalize() for word in others)
    return f"{name}_" if name in _NAMES_IN_TESTS or name == class_name else name


def _entry_path(project: Project) -> str:
    """The entry file relative to the test files, as an import names it."""
    path = posixpath.relpath(project.entry, project.tests)
    return path if path.startswith(_PARENT_DIRECTORY) else f"{_CURRENT_DIRECTORY}{path}"


def _comment(text: str) -> list[str]:
    """`text` on one line as `//` comments, wrapped within the line length; none when blank."""
    return textwrap.wrap(
        " ".join(text.split()),
        width=PRINT_WIDTH,
        initial_indent=COMMENT,
        subsequent_indent=COMMENT,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _width(text: str) -> int:
    """Columns as Prettier counts them: wide characters take two; control characters,
    combining marks and variation selectors none."""
    if text.isascii():
        return len(text)
    return sum(_character_width(character) for character in text)


def _character_width(character: str) -> int:
    code = ord(character)
    if any(code in invisible for invisible in _INVISIBLE):
        return 0
    return 2 if unicodedata.east_asian_width(character) in _WIDE else 1


_STYLE = Style(PRINT_WIDTH, INDENT, _width)
"""How Prettier lays out a statement: its print width, indentation and column count."""
