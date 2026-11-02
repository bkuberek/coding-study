"""`testing` files for the levels of a Go project problem
(docs/specs/problem-format.md#go-test-files).

A level's file is an external test package, `package <tests directory>_test`, that imports the
entry's package by its import path, as the grader does, under an explicit name: the entry's
directory name, or the entry file's name for an entry at the root (`bank "bank-project-go"`). Each
test replays one visible case: it builds the entry type with its constructor, then turns each call
into one statement in the method's Go name. A `void` method's call stands alone; any other call is
checked in an `if got := ...; <mismatch> {` that reports the call, the result and the expected
value with `t.Errorf`. `exact` compares scalars and dates with `!=`, booleans as conditions,
decimals with `Equal`, and lists with `slices.Equal`, or `slices.EqualFunc` through nested lists and
lists of decimals; `unordered` sorts the result first (`slices.Sorted`, or `slices.SortedFunc` with
`slices.Compare`, `decimal.Decimal.Cmp` or `time.Time.Compare`) against a literal already sorted
that way; `float` calls `closeTo`, defined once in the file when used, which holds exactly when
`abs(a - e) <= tol * max(1, abs(e))`.

On the virtual clock (docs/specs/problem-format.md#generated-tests-on-the-virtual-clock) each test
runs its body in `synctest.Test`, as the grader runs a case in a bubble of its own, and calls
`synctest.Wait()` between operations, as the grader settles after each. `@advance` is `time.Sleep`,
`@spawn` a goroutine that sends the call's result on a channel of the task's name (closing it for a
`void` method), `@join` a receive from that channel, checked as any call is, and `@now` the
milliseconds since the `start` the test read before it built the instance.

gofmt never breaks or joins lines, so a file needs only gofmt's spacing, tab indentation and
import grouping to be as gofmt leaves it: standard-library imports first, then the others, each
group sorted by path.
"""

import itertools
import json
import posixpath
import re
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from coding_study.adapters.languages.go.stub_generator import INDENT, go_type
from coding_study.domain.cases import JsonValue
from coding_study.domain.naming import (
    RESERVED_WORDS,
    NameRole,
    constructor_name,
    member_name,
    snake_case,
)
from coding_study.domain.problem import ComparatorType, Language
from coding_study.domain.project import PATH_SEPARATOR
from coding_study.domain.project_tests import (
    EDIT_NOTICE,
    Advance,
    Call,
    Join,
    LevelTest,
    LevelTests,
    Now,
    Operation,
    Spawn,
)
from coding_study.domain.signature import Method
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeType,
    ReturnType,
    Scalar,
    ScalarType,
    ValueType,
    VoidType,
)

COMMENT = "// "
COMMENT_WIDTH = 100
TEST_PACKAGE_SUFFIX = "_test"
TESTING = "testing"
SYNCTEST = "testing/synctest"
MATH = "math"
SLICES = "slices"
TIME = "time"
DECIMAL = "github.com/shopspring/decimal"
CLOSE_TO = "closeTo"
GOT = "got"
START = "start"
"""The time the test of a virtual-clock project read before it built the instance."""
FALLBACK_ALIAS = "entry"
FALLBACK_INSTANCE = "subject"
FALLBACK_TASK = "task"
_STANDARD_LIBRARY = frozenset({TESTING, SYNCTEST, MATH, SLICES, TIME})
_ORDERED = frozenset({Scalar.INT, Scalar.LONG, Scalar.DOUBLE, Scalar.STRING, Scalar.CHAR})
"""What `cmp.Ordered` covers, so `slices.Sorted` and `slices.Compare` take it."""
_ESCAPES = {
    **{"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"},
    **{"\a": "\\a", "\b": "\\b", "\f": "\\f", "\v": "\\v"},
}
_LAST_BYTE_ESCAPE = 0xFF
_LAST_SHORT_ESCAPE = 0xFFFF
_RAW_STRING_QUOTE = "`"
_NOT_IDENTIFIER = re.compile(r"[^A-Za-z0-9_]")
_MONTHS = (
    *("January", "February", "March", "April", "May", "June"),
    *("July", "August", "September", "October", "November", "December"),
)
_SORT_FUNCTIONS = {Scalar.DECIMAL: "decimal.Decimal.Cmp", Scalar.DATE: "time.Time.Compare"}
_SCALAR_IMPORTS = {Scalar.DECIMAL: DECIMAL, Scalar.DATE: TIME}
"""The package whose type a scalar is in Go."""


class GoTestGenerator:
    """`ProjectTestGenerator` for Go's `testing`: `<tests>/level_<n>_test.go`."""

    def generate(self, tests: LevelTests) -> str:
        return _LevelFile(tests).text()


@dataclass(frozen=True, slots=True)
class _Value:
    """A Go expression and the imports it needs."""

    text: str
    imports: frozenset[str] = field(default_factory=frozenset[str])


class _LevelFile:
    def __init__(self, tests: LevelTests) -> None:
        self._tests = tests
        self._alias = _entry_alias(tests.entry)
        self._instance = _instance_name(tests.signature.name, self._alias)
        self._imports: set[str] = {TESTING, *([SYNCTEST] if tests.virtual_clock else [])}
        self._compares_floats = False

    def text(self) -> str:
        header = "\n".join([*_comment(self._tests.title), *_comment(EDIT_NOTICE)])
        package = f"package {_test_package(self._tests.project.tests)}"
        if not self._tests.tests:
            return f"{header}\n\n{package}\n"
        tests = [self._test(test) for test in self._tests.tests]
        helper = [_close_to(self._tests.tolerance)] if self._compares_floats else []
        blocks = [header, package, self._import_block(), *helper, *tests]
        return "\n\n".join(blocks) + "\n"

    def _import_block(self) -> str:
        entry = f'{self._alias} "{_entry_import_path(self._tests.slug, self._tests.entry)}"'
        standard = sorted(path for path in self._imports if path in _STANDARD_LIBRARY)
        others = sorted(
            [(path, f'"{path}"') for path in self._imports if path not in _STANDARD_LIBRARY]
            + [(_entry_import_path(self._tests.slug, self._tests.entry), entry)]
        )
        groups = [[f'"{path}"' for path in standard], [line for _, line in others]]
        body = "\n\n".join("\n".join(f"{INDENT}{line}" for line in group) for group in groups)
        return f"import (\n{body}\n)"

    def _test(self, test: LevelTest) -> str:
        lines = [
            *_comment(test.note or ""),
            f"func Test{_test_name(test.case_id)}(t *testing.T) {{",
        ]
        body = self._body(test)
        if self._tests.virtual_clock:
            body = ["synctest.Test(t, func(t *testing.T) {", *_indented(body), "})"]
        lines += _indented(body)
        return "\n".join([*lines, "}"])

    def _body(self, test: LevelTest) -> list[str]:
        """The test's statements, a group per operation, the constructor's first. On the virtual
        clock the case settles between two operations."""
        names = _TaskNames(self._instance, self._alias)
        groups = [self._construction(test), *(self._operation(op, names) for op in test.operations)]
        if not self._tests.virtual_clock:
            return [line for group in groups for line in group]
        settled = [line for group in groups[:-1] for line in (*group, "synctest.Wait()")]
        return [*self._clock_start(test), *settled, *groups[-1]]

    def _clock_start(self, test: LevelTest) -> list[str]:
        if not any(isinstance(operation, Now) for operation in test.operations):
            return []
        self._imports.add(TIME)
        return [f"{START} := {TIME}.Now()"]

    def _construction(self, test: LevelTest) -> list[str]:
        signature = self._tests.signature
        arguments = self._arguments(
            test.constructor_arguments, [param.type for param in signature.constructor_params]
        )
        constructor = constructor_name(signature.name, Language.GO) or f"New{signature.name}"
        construction = f"{self._alias}.{constructor}({arguments})"
        uses_instance = any(isinstance(op, Call | Spawn) for op in test.operations)
        return [f"{self._instance} := {construction}" if uses_instance else construction]

    def _operation(self, operation: Operation, names: "_TaskNames") -> list[str]:
        match operation:
            case Call():
                return self._call(operation)
            case Advance(milliseconds):
                self._imports.add(TIME)
                return [f"time.Sleep({milliseconds} * time.Millisecond)"]
            case Spawn():
                return self._spawn(operation, names)
            case Join(task, call):
                return self._checked(f"<-{names.variable(task)}", call)
            case Now(expected):
                self._imports.add(TIME)
                found = ScalarType(Scalar.LONG)
                reading = f"{TIME}.Since({START}).Milliseconds()"
                return self._check_result(reading, found, expected, ComparatorType.EXACT)

    def _call(self, call: Call) -> list[str]:
        return self._checked(self._invocation(call.method, call.arguments), call)

    def _invocation(self, method: Method, arguments: Sequence[JsonValue]) -> str:
        name = member_name(method.name, Language.GO, NameRole.METHOD)
        types = [param.type for param in method.params]
        return f"{self._instance}.{name}({self._arguments(arguments, types)})"

    def _spawn(self, spawn: Spawn, names: "_TaskNames") -> list[str]:
        variable = names.assign(spawn.task)
        invocation = self._invocation(spawn.method, spawn.arguments)
        returns = spawn.method.returns.type
        if isinstance(returns, VoidType):
            return [
                f"{variable} := make(chan struct{{}})",
                f"go func() {{ {invocation}; close({variable}) }}()",
            ]
        self._imports |= _type_imports(returns)
        return [
            f"{variable} := make(chan {go_type(returns)}, 1)",
            f"go func() {{ {variable} <- {invocation} }}()",
        ]

    def _checked(self, invocation: str, call: Call) -> list[str]:
        """`invocation` alone when the method returns nothing, otherwise its result checked."""
        if not call.returns_value:
            return [invocation]
        returns = call.method.returns.type
        return self._check_result(invocation, returns, call.expected, call.comparator)

    def _check_result(
        self, invocation: str, returns: ReturnType, expected: JsonValue, comparator: ComparatorType
    ) -> list[str]:
        assert not isinstance(returns, VoidType)
        check = self._check(expected, comparator, returns)
        tested = check.sorting.applied(invocation) if check.sorting else invocation
        called = f"{invocation} sorted" if check.sorting else invocation
        message = _format_string(called, f"{check.expected}{check.within}")
        return [
            f"if {GOT} := {tested}; {check.mismatch} {{",
            f"{INDENT}t.Errorf({message}, {GOT})",
            "}",
        ]

    def _check(
        self, expected: JsonValue, comparator: ComparatorType, returns: ValueType
    ) -> "_Check":
        floats = comparator is ComparatorType.FLOAT and _holds_numbers(expected)
        if floats:
            self._compares_floats = True
            self._imports.add(MATH)
        sorting = None
        if comparator is ComparatorType.UNORDERED and isinstance(expected, list):
            sorting = self._sorting(_element(returns))
            in_order: list[JsonValue] = sorted(expected, key=lambda item: _sort_key(item, returns))
            expected = in_order
        value = self._value(expected, returns)
        mismatch = self._mismatch(returns, value.text, expected, floats=floats)
        within = f" within {_float(self._tests.tolerance)}" if floats else ""
        return _Check(mismatch, value.text, sorting, within)

    def _sorting(self, element: ValueType) -> "_Sorting":
        """How a result of `element` items is sorted before it is compared.

        Raises ValueError for items Go's sorts cannot order without a comparison of their own.
        """
        self._imports.add(SLICES)
        match element:
            case ScalarType(scalar) if scalar in _ORDERED:
                return _Sorting()
            case ScalarType(scalar) if scalar in _SORT_FUNCTIONS:
                self._imports.add(DECIMAL if scalar is Scalar.DECIMAL else TIME)
                return _Sorting(_SORT_FUNCTIONS[scalar])
            case ArrayType(ScalarType(scalar)) | ListType(ScalarType(scalar)) if scalar in _ORDERED:
                return _Sorting("slices.Compare")
            case _:
                raise ValueError(f"a generated Go test cannot sort a list of {element}")

    def _mismatch(
        self, returns: ValueType, expected: str, value: JsonValue, *, floats: bool
    ) -> str:
        match returns:
            case ScalarType(Scalar.BOOL) if isinstance(value, bool):
                return f"!{GOT}" if value else GOT
            case ScalarType(Scalar.DOUBLE) if floats:
                return f"!{CLOSE_TO}({GOT}, {expected})"
            case ScalarType(Scalar.DECIMAL):
                return f"!{GOT}.Equal({expected})"
            case ArrayType(element) | ListType(element):
                self._imports.add(SLICES)
                equal = self._equality(element, floats=floats)
                if equal is None:
                    return f"!slices.Equal({GOT}, {expected})"
                return f"!slices.EqualFunc({GOT}, {expected}, {equal})"
            case _:
                return f"{GOT} != {expected}"

    def _equality(self, declared: ValueType, *, floats: bool) -> str | None:
        """The function `slices.EqualFunc` compares items of type `declared` with; None for items
        that `==` compares."""
        match declared:
            case ScalarType(Scalar.DOUBLE) if floats:
                return CLOSE_TO
            case ScalarType(Scalar.DECIMAL):
                return "decimal.Decimal.Equal"
            case ArrayType(element) | ListType(element):
                inner = self._equality(element, floats=floats)
                if inner is None:
                    return "slices.Equal"
                spelled = go_type(declared)
                return f"func(a, b {spelled}) bool {{ return slices.EqualFunc(a, b, {inner}) }}"
            case _:
                return None

    def _arguments(self, values: Sequence[JsonValue], types: Sequence[ValueType]) -> str:
        pairs = zip(values, types, strict=True)
        return ", ".join(self._value(value, declared).text for value, declared in pairs)

    def _value(self, value: JsonValue, declared: ValueType) -> _Value:
        found = _literal(value, declared, elided=False)
        self._imports |= found.imports
        return found


@dataclass(frozen=True, slots=True)
class _Sorting:
    """The sort of an `unordered` result."""

    compare: str | None = None
    """The function `slices.SortedFunc` orders items with; None for `slices.Sorted`."""

    def applied(self, invocation: str) -> str:
        values = f"slices.Values({invocation})"
        if self.compare is None:
            return f"slices.Sorted({values})"
        return f"slices.SortedFunc({values}, {self.compare})"


@dataclass(frozen=True, slots=True)
class _Check:
    mismatch: str
    expected: str
    sorting: _Sorting | None
    """How an `unordered` result is sorted first; None for the other comparators."""
    within: str
    """The tolerance a `float` comparison allows, as the message names it."""


def _literal(value: JsonValue, declared: ValueType, *, elided: bool) -> _Value:
    """A Go literal of `value` as type `declared`; inside a composite literal a slice's type is
    left out (`{1, 2}`), as `gofmt -s` writes it."""
    match declared:
        case ScalarType(scalar):
            return _scalar(value, scalar)
        case ArrayType(element) | ListType(element):
            if not isinstance(value, list):
                raise ValueError(f"no Go literal of {declared} for {value!r}")
            items = [_literal(item, element, elided=True) for item in value]
            imports = frozenset[str]().union(*(item.imports for item in items))
            body = ", ".join(item.text for item in items)
            prefix = "" if elided else go_type(declared)
            return _Value(f"{prefix}{{{body}}}", imports)
        case NodeType():
            raise ValueError(f"a project test has no node values ({declared})")


def _scalar(value: JsonValue, scalar: Scalar) -> _Value:
    match scalar, value:
        case Scalar.BOOL, bool():
            return _Value("true" if value else "false")
        case Scalar.INT | Scalar.LONG, int() if not isinstance(value, bool):
            return _Value(str(value))
        case Scalar.DOUBLE, int() | float() if not isinstance(value, bool):
            return _Value(_float(value))
        case Scalar.STRING, str():
            return _Value(_string(value))
        case Scalar.CHAR, str():
            return _Value(_rune(value))
        case Scalar.DECIMAL, str():
            return _Value(f"decimal.RequireFromString({_string(value)})", frozenset({DECIMAL}))
        case Scalar.DATE, str():
            return _Value(_date(value), frozenset({TIME}))
        case _:
            raise ValueError(f"no Go literal of {scalar} for {value!r}")


def _float(value: float) -> str:
    """Python's shortest form reads back as the same float64 in Go (`2.5`, `1e-06`)."""
    return str(value) if isinstance(value, int) else repr(value)


def _date(text: str) -> str:
    day = date.fromisoformat(text)
    month = _MONTHS[day.month - 1]
    return f"time.Date({day.year}, time.{month}, {day.day}, 0, 0, 0, 0, time.UTC)"


def _string(text: str) -> str:
    return '"' + "".join(_escaped(character, '"') for character in text) + '"'


def _rune(text: str) -> str:
    return "'" + _escaped(text, "'") + "'"


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
    if code <= _LAST_SHORT_ESCAPE:
        return f"\\u{code:04x}"
    return f"\\U{code:08x}"


def _format_string(call: str, expected: str) -> str:
    """The `t.Errorf` format `<call> = %v, want <expected>`: a raw string unless it holds a
    backquote."""
    format_text = f"{_percents_kept(call)} = %v, want {_percents_kept(expected)}"
    if _RAW_STRING_QUOTE not in format_text:
        return f"{_RAW_STRING_QUOTE}{format_text}{_RAW_STRING_QUOTE}"
    return json.dumps(format_text, ensure_ascii=False)


def _percents_kept(text: str) -> str:
    return text.replace("%", "%%")


def _close_to(tolerance: float) -> str:
    return (
        f"func {CLOSE_TO}(got, want float64) bool {{\n"
        f"{INDENT}return math.Abs(got-want) <= {_float(tolerance)}*math.Max(1, math.Abs(want))\n"
        "}"
    )


def _element(declared: ValueType) -> ValueType:
    if isinstance(declared, ArrayType | ListType):
        return declared.element
    raise ValueError(f"{declared} is not a list")


def _sort_key(value: JsonValue, declared: ValueType) -> Any:
    """What the Go sort of a `declared` list compares: a decimal's value; strings by code point,
    which is how Go compares their UTF-8 bytes; dates as their ISO text; the rest as they are."""
    if _element(declared) == ScalarType(Scalar.DECIMAL):
        return Decimal(str(value))
    return value


def _holds_numbers(value: JsonValue) -> bool:
    if isinstance(value, list):
        return any(_holds_numbers(item) for item in value)
    return isinstance(value, int | float) and not isinstance(value, bool)


def _test_name(case_id: str) -> str:
    """`ex1` is `Ex1`, `l2-ex1` is `L2_ex1`: case ids hold no `_`, so no two ids collide."""
    name = case_id.replace("-", "_")
    return name[:1].upper() + name[1:]


def _test_package(tests: str) -> str:
    return f"{tests.rpartition(PATH_SEPARATOR)[2]}{TEST_PACKAGE_SUFFIX}"


def _entry_import_path(slug: str, entry: str) -> str:
    """The module is the slug (check S15); the entry's package is its file's directory."""
    directory = posixpath.dirname(entry)
    return f"{slug}{PATH_SEPARATOR}{directory}" if directory else slug


def _entry_alias(entry: str) -> str:
    """The entry directory's name, or the entry file's name for an entry at the root, as a Go
    identifier."""
    directory = posixpath.dirname(entry)
    name = posixpath.basename(directory) if directory else posixpath.splitext(entry)[0]
    alias = _NOT_IDENTIFIER.sub("", name).lower()
    usable = alias and not alias[0].isdigit() and alias not in RESERVED_WORDS[Language.GO]
    return alias if usable else FALLBACK_ALIAS


def _used_names(alias: str) -> set[str]:
    """The names a test already uses, which its instance and its tasks must not take."""
    taken = {"t", GOT, START, alias, CLOSE_TO, *RESERVED_WORDS[Language.GO]}
    return taken | {posixpath.basename(path) for path in (*_STANDARD_LIBRARY, DECIMAL)}


def _instance_name(class_name: str, alias: str) -> str:
    """The class's first letter in lower case (`b` for `Bank`), unless a name the test uses
    takes it: then the class in lowerCamelCase, then `subject`."""
    words = snake_case(class_name).split("_")
    camel = words[0] + "".join(word.capitalize() for word in words[1:])
    taken = _used_names(alias)
    candidates = (class_name[:1].lower(), camel, FALLBACK_INSTANCE)
    return next(name for name in candidates if name and name not in taken)


class _TaskNames:
    """The variables of one test's tasks, each the channel its goroutine answers on: the task's
    name as a Go identifier, else `task1`, `task2`, unless the test already uses the name."""

    def __init__(self, instance: str, alias: str) -> None:
        self._taken = _used_names(alias) | {instance}
        self._variables: dict[str, str] = {}

    def assign(self, task: str) -> str:
        spelled = _NOT_IDENTIFIER.sub("", task)
        fallbacks = (f"{FALLBACK_TASK}{number}" for number in itertools.count(1))
        candidates = itertools.chain([spelled], fallbacks)
        usable = (name for name in candidates if name and not name[0].isdigit())
        variable = next(name for name in usable if name not in self._taken)
        self._taken.add(variable)
        self._variables[task] = variable
        return variable

    def variable(self, task: str) -> str:
        return self._variables[task]


def _type_imports(declared: ValueType) -> frozenset[str]:
    """The packages whose types `go_type(declared)` spells."""
    match declared:
        case ScalarType(scalar):
            return (
                frozenset({_SCALAR_IMPORTS[scalar]}) if scalar in _SCALAR_IMPORTS else frozenset()
            )
        case ArrayType(element) | ListType(element):
            return _type_imports(element)
        case NodeType():
            return frozenset()


def _indented(lines: Sequence[str]) -> list[str]:
    return [f"{INDENT}{line}" for line in lines]


def _comment(text: str) -> list[str]:
    """`text` as `//` comments, wrapped within the line length; none when blank."""
    return textwrap.wrap(
        " ".join(text.split()),
        width=COMMENT_WIDTH,
        initial_indent=COMMENT,
        subsequent_indent=COMMENT,
        break_long_words=False,
        break_on_hyphens=False,
    )
