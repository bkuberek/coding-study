"""libtest files for the levels of a Rust project problem
(docs/specs/problem-format.md#rust-projects).

Each level's file is an integration test, `tests/level_<n>.rs`, a crate of its own that uses the
project's library. Each test replays one visible case: it builds the entry class with `new`, then
turns each call into one statement in the method's Rust name. A call to a method that returns
nothing stands alone; any other call is an assertion with the method's comparator: `assert!` for a
`bool`, `assert_eq!` for any other `exact` value, `sorted(...)` against a list already in Rust's
order for `unordered`, and the helpers `assert_close` and `assert_all_close` for `float`. Each
helper is defined once in the file when used. Values are Rust literals: a `String` argument is
`"ivy".to_string()` while an expected `String` is the literal, which `String` compares with; a
`decimal` is `Decimal::from_str_exact("2.50").unwrap()`, a `date`
`NaiveDate::from_ymd_opt(2026, 1, 1).unwrap()`, and an expected empty list `Vec::<T>::new()`.

The text already matches rustfmt with its default options, so no formatter runs. rustfmt lays out
a statement that does not fit its 100 columns, or a call whose arguments are wider than 60 columns
(`fn_call_width`, `array_width`), in a few ways that the expressions of a test use:

- a call with a single argument that does not fit lets that argument overflow the call when it is
  a call or a list itself: `assert!(!bank.create_account(` with the inner arguments below it;
- otherwise each argument goes on a line of its own, four columns in, with a trailing comma, except
  inside a macro's arguments, where rustfmt adds none;
- arguments that are all literals of at most 10 columns are packed onto as few lines as fit, and a
  list of such items stays on one line whenever it fits, whatever its width;
- a call on a receiver longer than four columns (`lru_cache.get(...)`) moves the call to a line of
  its own when that takes fewer lines than breaking its arguments;
- `let mut x = ...` moves the constructor to the next line when it then fits on one.
"""

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any

from coding_study.adapters.languages.rust.bridge import rust_string
from coding_study.adapters.languages.rust.types import rust_name, rust_type
from coding_study.domain.cases import JsonValue
from coding_study.domain.naming import RESERVED_WORDS, NameRole, rust_identifier, snake_case
from coding_study.domain.problem import ComparatorType, Language
from coding_study.domain.project_tests import EDIT_NOTICE, Call, LevelTest, LevelTests
from coding_study.domain.signature import output_type
from coding_study.domain.type_dsl import ArrayType, ListType, Scalar, ScalarType, ValueType

MAX_WIDTH = 100
INDENT = "    "
CALL_WIDTH = 60
"""rustfmt's `fn_call_width` and `array_width`: wider arguments are not kept on one line."""
SHORT_ITEM_WIDTH = 10
"""rustfmt's `short_array_element_width_threshold`: items this narrow may share lines."""
JOINED_RECEIVER_WIDTH = len(INDENT)
"""A receiver at most this wide stays on the line of the method call rustfmt breaks."""
CHAIN_OVERFLOW_LINES = 5
"""A call broken over at least this many lines stays on its receiver's line."""
TEST_PREFIX = "case_"
DOC_PREFIX = "///"
HEADER_PREFIX = "//!"
DATE_IMPORT = "use chrono::NaiveDate;"
DECIMAL_IMPORT = "use rust_decimal::Decimal;"
SORTED = "sorted"
ASSERT_CLOSE = "assert_close"
ASSERT_ALL_CLOSE = "assert_all_close"
HELPERS = {
    SORTED: """\
fn sorted<T: Ord>(mut items: Vec<T>) -> Vec<T> {
    items.sort();
    items
}""",
    ASSERT_CLOSE: """\
fn assert_close(actual: f64, expected: f64, tolerance: f64) {
    let bound = tolerance * expected.abs().max(1.0);
    assert!(
        (actual - expected).abs() <= bound,
        "{actual} is not within {bound} of {expected}"
    );
}""",
    ASSERT_ALL_CLOSE: """\
fn assert_all_close(actual: Vec<f64>, expected: Vec<f64>, tolerance: f64) {
    assert_eq!(
        actual.len(),
        expected.len(),
        "{actual:?} and {expected:?} differ in length"
    );
    for (item, wanted) in actual.into_iter().zip(expected) {
        assert_close(item, wanted, tolerance);
    }
}""",
}
"""Each helper as rustfmt lays it out, in the order the file defines them."""
_HELPERS_NEEDED = {ASSERT_ALL_CLOSE: (ASSERT_CLOSE,)}
_NAMES_IN_TESTS = frozenset({*RESERVED_WORDS[Language.RUST], *HELPERS})
"""What the instance may not be called: keywords, and the helpers a test calls."""
_SENTENCE_ENDINGS = (".", "!", "?")
_CHAR_ESCAPES = {"\\": "\\\\", "'": "\\'", "\n": "\\n", "\r": "\\r", "\t": "\\t", "\0": "\\0"}


# expressions, as rustfmt sees them


@dataclass(frozen=True, slots=True)
class _Atom:
    """Text rustfmt never breaks: a literal, a variable, or a short call chain."""

    text: str
    simple: bool = True
    """A literal or a plain name, which rustfmt lets share lines with others."""


@dataclass(frozen=True, slots=True)
class _Call:
    callee: str
    """`bank.deposit`, `Bank::new`, `assert_eq!`, `vec!`."""
    arguments: tuple["_Expression", ...]
    macro: bool = False
    """A macro other than `vec!`: rustfmt adds no trailing comma to its arguments."""
    list: bool = False
    """`vec![...]`, which rustfmt formats as an array."""


@dataclass(frozen=True, slots=True)
class _Not:
    operand: "_Expression"


@dataclass(frozen=True, slots=True)
class _MethodCall:
    """`receiver.method(...)`, a call chain of one link."""

    receiver: str
    call: _Call
    """The call, its callee the method's name."""


type _Expression = _Atom | _Call | _Not | _MethodCall


@dataclass(frozen=True, slots=True)
class _Shape:
    indent: int
    """The block indentation of lines after the first."""
    width: int
    """The columns left on the first line, from where the expression starts, when the expression
    ends on it: what follows it (`trailing`) is already left out."""
    offset: int = 0
    """How far right of `indent` the expression starts on its first line."""
    in_macro: bool = False
    """Inside a macro's arguments, where rustfmt adds no trailing comma."""
    trailing: int = 1
    """The columns that follow the expression on its last line: `;`, `,` or closing brackets."""

    def moved(self, columns: int) -> "_Shape":
        """The shape of what starts `columns` further right on the same line."""
        return replace(self, width=self.width - columns, offset=self.offset + columns)


class _UnfitError(Exception):
    """A layout rustfmt does not take: a method call it must keep on one line (in a function's
    arguments it overflows) would put the call on a line of its own."""


def _flat(expression: _Expression) -> str:
    match expression:
        case _Atom(text):
            return text
        case _Not(operand):
            return f"!{_flat(operand)}"
        case _MethodCall(receiver, call):
            return f"{receiver}.{_flat(call)}"
        case _Call():
            opening, closing = _delimiters(expression)
            inner = ", ".join(_flat(argument) for argument in expression.arguments)
            return f"{expression.callee}{opening}{inner}{closing}"


def _layout(expression: _Expression, shape: _Shape, *, one_line_chain: bool = False) -> str:
    """`expression` as rustfmt lays it out where it starts with `shape.width` columns left.

    Raises _UnfitError, with `one_line_chain`, for a method call that would go on a line of
    its own.
    """
    match expression:
        case _Atom(text):
            return text
        case _Not(operand):
            return "!" + _layout(operand, shape.moved(1), one_line_chain=one_line_chain)
        case _MethodCall():
            return _method_call(expression, shape, one_line_chain=one_line_chain)
        case _Call():
            return _call(expression, shape)


def _call(call: _Call, shape: _Shape) -> str:
    opening, closing = _delimiters(call)
    room = shape.width - _width(call.callee) - len(opening) - len(closing)
    arguments = call.arguments
    if not arguments:
        return f"{call.callee}{opening}{closing}"
    if len(arguments) == 1:
        single = _single(call, shape, room)
        if single is not None:
            return single
    else:
        joined = ", ".join(_flat(argument) for argument in arguments)
        fits = _width(joined) <= min(room, CALL_WIDTH)
        if not fits and shape.in_macro and _packable(arguments):
            fits = _bytes(joined) <= room
        if fits:
            return f"{call.callee}{opening}{joined}{closing}"
    return _broken(call, shape)


def _single(call: _Call, shape: _Shape, room: int) -> str | None:
    """A call of one argument: overflowed by it, when it is a call or a list
    (`assert!(!bank.create_account(` with the inner arguments below), else on one line when it
    fits there laid out on a line of its own. A macro or a list keeps it inline one column past
    its room, since rustfmt does not count the closing bracket there. None when neither: the
    argument goes on a line of its own."""
    opening, closing = _delimiters(call)
    (argument,) = call.arguments
    if _overflows(argument):
        overflowed = _overflowed(call, shape, room)
        if overflowed is not None:
            return overflowed
    own_line = _layout_on_own_line(argument, shape, call)
    slack = 1 if call.macro or call.list else 0
    if "\n" not in own_line and _width(own_line) <= room + slack:
        return f"{call.callee}{opening}{own_line}{closing}"
    return None


def _overflowed(call: _Call, shape: _Shape, room: int) -> str | None:
    """`callee(` and its one argument laid out after it, or None when rustfmt does not do so: a
    nested call or list overflows within 60 columns; a method call in a function's arguments
    only without going to a line of its own; an argument whose first line is wider than 60
    columns does not overflow. An argument that would break exactly once is laid out on a line
    of its own instead and, when that fits on one line, put back inline whenever it fits before
    the call's closing bracket, which rustfmt then does not count: such a line may end in column
    101."""
    opening, closing = _delimiters(call)
    (argument,) = call.arguments
    width = min(room, CALL_WIDTH) if _nested_call(argument) else room
    columns = _width(call.callee) + len(opening)
    inner_shape = replace(
        shape.moved(columns),
        width=width,
        in_macro=_inner_macro(call, shape),
        trailing=shape.trailing + len(closing),
    )
    forced = _method_chain(argument) and not call.macro
    try:
        inner = _layout(argument, inner_shape, one_line_chain=forced)
    except _UnfitError:
        return None
    if "\n" not in inner:
        return f"{call.callee}{opening}{inner}{closing}" if _width(inner) <= width else None
    if _width(inner.split("\n", 1)[0]) > min(room, CALL_WIDTH):
        return None
    if inner.count("\n") == 1:
        own_line = _layout_on_own_line(argument, shape, call)
        if "\n" not in own_line:
            fits = _width(own_line) + len(closing) <= shape.width - _width(call.callee)
            return f"{call.callee}{opening}{own_line}{closing}" if fits else None
    return f"{call.callee}{opening}{inner}{closing}"


def _layout_on_own_line(argument: _Expression, shape: _Shape, call: _Call) -> str:
    nested = shape.indent + len(INDENT)
    own_line = _Shape(nested, MAX_WIDTH - nested - 1, in_macro=_inner_macro(call, shape))
    return _layout(argument, own_line)


def _broken(call: _Call, shape: _Shape) -> str:
    """Each argument on a line of its own, or literals packed onto as few lines as fit, four
    columns in; with a trailing comma, except in a macro's arguments."""
    opening, closing = _delimiters(call)
    nested = shape.indent + len(INDENT)
    in_macro = _inner_macro(call, shape)
    trailing = "" if in_macro else ","
    if _packable(call.arguments):
        flats = [_flat(argument) for argument in call.arguments]
        lines = _packed(flats, MAX_WIDTH - nested - 1, trailing)
    else:
        item_shape = _Shape(nested, MAX_WIDTH - nested - 1, in_macro=in_macro)
        laid_out = [_layout(argument, item_shape) for argument in call.arguments]
        if _horizontal_lone_item(call, laid_out):
            trailing = ""
        lines = [f"{text}," for text in laid_out[:-1]] + [laid_out[-1] + trailing]
    body = "\n".join(_indented(line, nested) for line in lines)
    return f"{call.callee}{opening}\n{body}\n{' ' * shape.indent}{closing}"


def _horizontal_lone_item(call: _Call, laid_out: Sequence[str]) -> bool:
    """A list's one item, on one line of at most 60 columns: rustfmt puts it on a line of its
    own without the trailing comma of a vertical list."""
    (item, *others) = laid_out
    return call.list and not others and "\n" not in item and _width(item) <= CALL_WIDTH


def _inner_macro(call: _Call, shape: _Shape) -> bool:
    """Whether the call's arguments are a macro's, where rustfmt adds no trailing comma: those of
    a macro, but for `vec!`, which it formats as an array, and anything inside them."""
    return shape.in_macro or call.macro


def _method_call(method: _MethodCall, shape: _Shape, *, one_line_chain: bool = False) -> str:
    """A call on a receiver. A receiver that ends at most four columns into its line (`bank` at
    a line's start) joins the call; any other stays on the call's line unless putting the call on
    a line of its own takes fewer lines, or the first line would not fit.

    Raises _UnfitError when `one_line_chain` forbids the call's own line.
    """
    receiver, call = method.receiver, method.call
    joined = _Call(f"{receiver}.{call.callee}", call.arguments, call.macro, call.list)
    if _width(receiver) <= JOINED_RECEIVER_WIDTH - shape.offset:
        return _layout(joined, shape)
    same_line = _layout(joined, shape)
    if "\n" not in same_line and _width(same_line) <= shape.width:
        return same_line
    first_line_fits = _width(same_line.split("\n", 1)[0]) <= shape.width
    lines = same_line.count("\n") + 1
    if not (first_line_fits and lines >= CHAIN_OVERFLOW_LINES):
        child_indent = shape.indent + len(INDENT)
        child_width = MAX_WIDTH - child_indent - len(".") - shape.trailing
        child_shape = _Shape(child_indent, child_width, 1, shape.in_macro, shape.trailing)
        own_line = f"{receiver}\n{' ' * child_indent}.{_layout(call, child_shape)}"
        if not first_line_fits or own_line.count("\n") + 1 < lines:
            if one_line_chain:
                raise _UnfitError
            return own_line
    return same_line


def _packed(items: Sequence[str], width: int, trailing: str) -> list[str]:
    """Items as rustfmt's mixed layout packs them, as many to a line as fit in `width`: each
    counted with its comma, but the last one only once the list has wrapped; the last one ends
    with `trailing`."""
    lines: list[list[str]] = [[]]
    used = 0
    for index, item in enumerate(items):
        last = index == len(items) - 1
        size = _width(item) + (0 if last and len(lines) == 1 else len(","))
        if lines[-1] and used + 1 + size > width:
            lines.append([])
            used = 0
        used += size + (1 if lines[-1] else 0)
        lines[-1].append(item)
    texts = [", ".join(line) + "," for line in lines]
    texts[-1] = texts[-1].removesuffix(",") + trailing
    return texts


def _packable(arguments: Sequence[_Expression]) -> bool:
    """Every argument a literal at most 10 columns wide."""
    return all(
        isinstance(argument, _Atom)
        and argument.simple
        and _bytes(argument.text) <= SHORT_ITEM_WIDTH
        for argument in arguments
    )


def _method_chain(expression: _Expression) -> bool:
    """A method call, perhaps negated: rustfmt keeps it on one line when it overflows a
    function's arguments."""
    match expression:
        case _Not(operand):
            return _method_chain(operand)
        case _MethodCall():
            return True
        case _Atom() | _Call():
            return False


def _nested_call(expression: _Expression) -> bool:
    """A call or a list, not a method call: rustfmt overflows it within 60 columns."""
    match expression:
        case _Not(operand):
            return _nested_call(operand)
        case _Call():
            return True
        case _Atom() | _MethodCall():
            return False


def _overflows(expression: _Expression) -> bool:
    match expression:
        case _Not(operand):
            return _overflows(operand)
        case _Call() | _MethodCall():
            return True
        case _Atom():
            return False


def _delimiters(call: _Call) -> tuple[str, str]:
    return ("[", "]") if call.list else ("(", ")")


def _indented(line: str, columns: int) -> str:
    return " " * columns + line


def _statement(expression: _Expression) -> str:
    """`expression;` in a test's body."""
    indent = len(INDENT)
    return f"{INDENT}{_layout(expression, _Shape(indent, MAX_WIDTH - indent - 1))};"


def _declaration(name: str, value: _Expression) -> str:
    """`let mut name = value;`, with the value on the next line when it then fits on one and
    does not on the first."""
    indent = len(INDENT)
    head = f"let mut {name} ="
    shape = _Shape(indent, MAX_WIDTH - indent - len(head) - 2, len(head) + 1)
    same_line = _layout(value, shape)
    if "\n" not in same_line and _width(same_line) <= shape.width:
        return f"{INDENT}{head} {same_line};"
    next_indent = indent + len(INDENT)
    next_line = _layout(value, _Shape(next_indent, MAX_WIDTH - next_indent - 1))
    if _prefers_next_line(same_line, next_line):
        return f"{INDENT}{head}\n{' ' * next_indent}{next_line};"
    return f"{INDENT}{head} {same_line};"


def _prefers_next_line(same_line: str, next_line: str) -> bool:
    if "\n" not in next_line:
        return True
    return same_line.count("\n") > next_line.count("\n") + 1


# the file


class RustTestGenerator:
    """`ProjectTestGenerator` for libtest: `tests/level_<n>.rs`."""

    def generate(self, tests: LevelTests) -> str:
        return _LevelFile(tests).text()


@dataclass
class _Uses:
    imports: set[str] = field(default_factory=set[str])
    helpers: set[str] = field(default_factory=set[str])


class _LevelFile:
    def __init__(self, tests: LevelTests) -> None:
        self._tests = tests
        self._class = tests.signature.name
        self._instance = _instance_name(self._class)
        self._uses = _Uses()
        self._values = _Values(self._uses)

    def text(self) -> str:
        functions = [self._function(test) for test in self._tests.tests]
        header = _header(self._tests.title)
        if not functions:
            return f"{header}\n"
        helpers = [HELPERS[name] for name in HELPERS if name in self._helpers()]
        blocks = [header, self._imports(), *helpers, *functions]
        return "\n\n".join(blocks) + "\n"

    def _helpers(self) -> set[str]:
        used = set(self._uses.helpers)
        for helper in self._uses.helpers:
            used.update(_HELPERS_NEEDED.get(helper, ()))
        return used

    def _imports(self) -> str:
        entry = f"use {self._tests.entry}::{self._class};"
        return "\n".join(sorted({entry, *self._uses.imports}))

    def _function(self, test: LevelTest) -> str:
        lines = [f"{DOC_PREFIX} {sentence}" for sentence in _note(test.note)]
        lines += ["#[test]", f"fn {_test_name(test.case_id)}() {{", self._construction(test)]
        lines += [self._statement(call) for call in test.calls]
        lines.append("}")
        return "\n".join(lines)

    def _construction(self, test: LevelTest) -> str:
        """`let mut bank = Bank::new(...);`, or the constructor alone when no call follows to use
        the instance."""
        types = [param.type for param in self._tests.signature.constructor_params]
        arguments = self._values.arguments(test.constructor_arguments, types)
        construction = _Call(f"{self._class}::new", arguments)
        if not test.calls:
            return _statement(construction)
        return _declaration(self._instance, construction)

    def _statement(self, call: Call) -> str:
        name = rust_name(call.method.name, NameRole.METHOD)
        types = [param.type for param in call.method.params]
        arguments = self._values.arguments(call.arguments, types)
        invocation = _MethodCall(self._instance, _Call(name, arguments))
        if not call.returns_value:
            return _statement(invocation)
        return _statement(self._assertion(invocation, call))

    def _assertion(self, invocation: _Expression, call: Call) -> _Expression:
        expected, declared = call.expected, output_type(call.method)
        match call.comparator:
            case ComparatorType.FLOAT if _holds_double(declared):
                return self._close(invocation, expected, declared, call)
            case ComparatorType.UNORDERED if isinstance(expected, list):
                if _holds_double(declared):
                    raise ValueError(_unorderable(call))
                self._uses.helpers.add(SORTED)
                ordered = sorted(expected, key=lambda value: _sort_key(value, _element(declared)))
                sorted_call = _Call(SORTED, (invocation,))
                return _Call(
                    "assert_eq!",
                    (sorted_call, self._values.expected(ordered, declared)),
                    macro=True,
                )
            case _ if isinstance(expected, bool):
                checked = invocation if expected else _Not(invocation)
                return _Call("assert!", (checked,), macro=True)
            case _:
                value = self._values.expected(expected, declared)
                return _Call("assert_eq!", (invocation, value), macro=True)

    def _close(
        self, invocation: _Expression, expected: JsonValue, declared: ValueType | None, call: Call
    ) -> _Expression:
        tolerance = _Atom(_float_literal(self._tests.tolerance))
        if isinstance(declared, ScalarType):
            self._uses.helpers.add(ASSERT_CLOSE)
            return _Call(
                ASSERT_CLOSE, (invocation, self._values.argument(expected, declared), tolerance)
            )
        element = _element(declared)
        if not isinstance(element, ScalarType):
            raise ValueError(
                f"a generated Rust test compares {call.method.name} with float only in double, "
                "double[] and list<double>"
            )
        self._uses.helpers.add(ASSERT_ALL_CLOSE)
        values = self._values.argument(expected, declared)
        return _Call(ASSERT_ALL_CLOSE, (invocation, values, tolerance))


class _Values:
    """Rust expressions for JSON values, and the imports they need."""

    def __init__(self, uses: _Uses) -> None:
        self._uses = uses

    def arguments(
        self, values: Sequence[JsonValue], types: Sequence[ValueType]
    ) -> tuple[_Expression, ...]:
        """Each value by its parameter's type."""
        return tuple(
            self.argument(value, types[index] if index < len(types) else None)
            for index, value in enumerate(values)
        )

    def argument(self, value: JsonValue, declared: ValueType | None) -> _Expression:
        """A value passed by value: a `String` is owned, and a list infers its type from the
        parameter, even an empty one."""
        if isinstance(value, list):
            element = _element(declared)
            return _Call("vec!", tuple(self.argument(item, element) for item in value), list=True)
        if isinstance(declared, ScalarType) and declared.scalar is Scalar.STRING:
            return _Atom(f"{_string_literal(value)}.to_string()", simple=False)
        return self._scalar(value, declared)

    def expected(self, value: JsonValue, declared: ValueType | None) -> _Expression:
        """A value a result is compared with: a `String` compares with a literal, and an empty
        list spells its type, which nothing else would tell."""
        if isinstance(value, list):
            if not value:
                return _Atom(f"Vec::<{_element_type(declared)}>::new()", simple=False)
            element = _element(declared)
            return _Call("vec!", tuple(self.expected(item, element) for item in value), list=True)
        if isinstance(declared, ScalarType) and declared.scalar is Scalar.STRING:
            return _Atom(_string_literal(value))
        return self._scalar(value, declared)

    def _scalar(self, value: JsonValue, declared: ValueType | None) -> _Expression:
        scalar = declared.scalar if isinstance(declared, ScalarType) else None
        match scalar:
            case Scalar.DECIMAL:
                self._uses.imports.add(DECIMAL_IMPORT)
                text = f"Decimal::from_str_exact({_string_literal(value)}).unwrap()"
                return _Atom(text, simple=False)
            case Scalar.DATE:
                self._uses.imports.add(DATE_IMPORT)
                year, month, day = (int(part) for part in str(value).split("-"))
                return _Atom(
                    f"NaiveDate::from_ymd_opt({year}, {month}, {day}).unwrap()", simple=False
                )
            case Scalar.DOUBLE:
                return _Atom(_float_literal(value))
            case Scalar.CHAR:
                return _Atom(_char_literal(value))
            case Scalar.STRING:
                return _Atom(_string_literal(value))
            case _:
                return _Atom(_literal(value))


def _element(declared: ValueType | None) -> ValueType | None:
    match declared:
        case ArrayType(element) | ListType(element):
            return element
        case _:
            return None


def _element_type(declared: ValueType | None) -> str:
    element = _element(declared)
    if element is None:
        raise ValueError(f"an empty list needs its type, not {declared}")
    return rust_type(element)


def _holds_double(declared: ValueType | None) -> bool:
    match declared:
        case ScalarType(scalar):
            return scalar is Scalar.DOUBLE
        case ArrayType(element) | ListType(element):
            return _holds_double(element)
        case _:
            return False


def _unorderable(call: Call) -> str:
    return (
        f"a generated Rust test cannot sort the result of {call.method.name}: "
        "doubles have no order in Rust (Ord)"
    )


def _sort_key(value: JsonValue, declared: ValueType | None) -> Any:
    """How Rust orders a value of the declared type: decimals by value, strings by their bytes,
    which is their code points' order, lists item by item."""
    match declared:
        case ScalarType(Scalar.DECIMAL) if isinstance(value, str):
            return Decimal(value)
        case _ if isinstance(value, list):
            element = _element(declared)
            return [_sort_key(item, element) for item in value]
        case _:
            return value


def _literal(value: JsonValue) -> str:
    match value:
        case bool():
            return "true" if value else "false"
        case int():
            return str(value)
        case float():
            return _float_literal(value)
        case _:
            raise ValueError(f"no Rust literal for {value!r}")


def _float_literal(value: JsonValue) -> str:
    """A double with a decimal point or an exponent, as Rust needs: `2.0`, `1e-05`."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"no Rust double for {value!r}")
    return repr(float(value))


def _string_literal(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise ValueError(f"no Rust string for {value!r}")
    return rust_string(value)


def _char_literal(value: JsonValue) -> str:
    if not isinstance(value, str) or len(value) != 1:
        raise ValueError(f"no Rust char for {value!r}")
    if value in _CHAR_ESCAPES:
        return f"'{_CHAR_ESCAPES[value]}'"
    if ord(value) < 0x20:
        return f"'\\u{{{ord(value):x}}}'"
    return f"'{value}'"


def _instance_name(class_name: str) -> str:
    """The class in snake case: `bank` for `Bank`, `lru_cache` for `LRUCache`."""
    name = snake_case(class_name)
    return f"{name}_" if name in _NAMES_IN_TESTS else name


def _test_name(case_id: str) -> str:
    """The case id as a function name: `-` as `_`, with `case_` before an id that is not a
    Rust identifier on its own."""
    name = case_id.replace("-", "_")
    if name[0].isdigit() or rust_identifier(name) != name or name in RESERVED_WORDS[Language.RUST]:
        return f"{TEST_PREFIX}{name}"
    return name


def _header(title: str) -> str:
    lines = [title, "", EDIT_NOTICE]
    return "\n".join(f"{HEADER_PREFIX} {line}".rstrip() for line in lines)


def _note(note: str | None) -> list[str]:
    """A case's note as one sentence."""
    text = " ".join((note or "").split())
    if not text:
        return []
    if text[0].isascii() and text[0].islower():
        text = text[0].upper() + text[1:]
    return [text if text.endswith(_SENTENCE_ENDINGS) else f"{text}."]


def _width(text: str) -> int:
    """Columns as rustfmt counts them: wide characters take two, combining marks none."""
    return sum(_character_width(character) for character in text)


def _character_width(character: str) -> int:
    if unicodedata.combining(character):
        return 0
    return 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1


def _bytes(text: str) -> int:
    """What rustfmt measures a macro's list of literals by, to keep it on one line: its UTF-8
    bytes."""
    return len(text.encode())
