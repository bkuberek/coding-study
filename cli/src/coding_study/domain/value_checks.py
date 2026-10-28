"""Case values against the signature: `cstudy verify` check S4 (docs/specs/authoring.md#static).

Ranges, char length, `decimal` and `date` strings (problem-format.md#decimal-and-date), node
encodings (problem-format.md#serialization-of-linked-structures), op names and arities, and
`long` at most 2^53-1. Inputs may encode a cyclic ListNode; expected outputs never do, and
expected trees have their trailing nulls trimmed like serialized ones. Inputs keep the scale of a
decimal; expected decimals are written in canonical form, as the runners encode them.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from coding_study.domain.cases import Case, FunctionInput, JsonValue, OperationSequence
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Signature,
)
from coding_study.domain.type_dsl import (
    ArrayType,
    ListType,
    NodeKind,
    NodeType,
    Scalar,
    ScalarType,
    ValueType,
    VoidType,
)
from coding_study.domain.value_text import value_text

INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
MAX_SAFE_LONG = 2**53 - 1
BMP_LIMIT = 0x10000
MAX_DECIMAL_DIGITS = 28
"""Python's default decimal context precision."""
DECIMAL_PATTERN = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
CYCLE_VALUES = "values"
CYCLE_AT = "cycle_at"


def input_value_issues(value: JsonValue, value_type: ValueType) -> list[str]:
    return _Rules(output=False).issues(value, value_type, "")


def output_value_issues(value: JsonValue, value_type: ValueType) -> list[str]:
    return _Rules(output=True).issues(value, value_type, "")


def case_issues(signature: Signature, case: Case) -> tuple[str, ...]:
    """Every problem with the case's input and expected value, each prefixed by its field."""
    if isinstance(signature, FunctionSignature):
        return tuple(_function_case(signature, case))
    return tuple(_class_case(signature, case))


def _issue(path: str, message: str) -> str:
    return f"{path}: {message}" if path else message


def _got(expected: str, value: JsonValue) -> str:
    return f"expected {expected}, got {value_text(value)}"


@dataclass(frozen=True, slots=True)
class _Rules:
    output: bool

    def issues(self, value: JsonValue, value_type: ValueType, path: str) -> list[str]:
        match value_type:
            case ScalarType(scalar=scalar):
                message = _scalar_problem(value, scalar, self.output)
                return [_issue(path, message)] if message else []
            case ArrayType(element=element) | ListType(element=element):
                if not isinstance(value, list):
                    return [_issue(path, _got("an array", value))]
                return self._elements(value, element, path)
            case NodeType(kind=kind):
                return self._node(value, kind, path)

    def _elements(self, values: Sequence[JsonValue], element: ValueType, path: str) -> list[str]:
        return [
            issue
            for index, item in enumerate(values)
            for issue in self.issues(item, element, f"{path}[{index}]")
        ]

    def _node(self, value: JsonValue, kind: NodeKind, path: str) -> list[str]:
        match kind:
            case NodeKind.LIST_NODE:
                return self._list_node(value, path)
            case NodeKind.TREE_NODE:
                return self._tree_node(value, path)
            case NodeKind.GRAPH_NODE:
                return _graph_node(value, path)

    def _list_node(self, value: JsonValue, path: str) -> list[str]:
        if isinstance(value, dict) and not self.output:
            return _cyclic_list(value, path)
        if not isinstance(value, list):
            return [_issue(path, _got("a list of node values", value))]
        return self._elements(value, ScalarType(Scalar.INT), path)

    def _tree_node(self, value: JsonValue, path: str) -> list[str]:
        if not isinstance(value, list):
            return [_issue(path, _got("a level-order array", value))]
        issues = [
            _issue(f"{path}[{index}]", _got("int or null", item))
            for index, item in enumerate(value)
            if item is not None and _integer_problem(item, Scalar.INT)
        ]
        if value and value[0] is None:
            issues.append(_issue(f"{path}[0]", "the root cannot be null (use [] for no tree)"))
        if self.output and value and value[-1] is None:
            issues.append(_issue(path, "trailing null (serialized trees trim them)"))
        return issues


def _scalar_problem(value: JsonValue, scalar: Scalar, output: bool) -> str | None:
    match scalar:
        case Scalar.INT | Scalar.LONG:
            return _integer_problem(value, scalar)
        case Scalar.DOUBLE:
            is_number = isinstance(value, int | float) and not isinstance(value, bool)
            return None if is_number else _got("double", value)
        case Scalar.BOOL:
            return None if isinstance(value, bool) else _got("bool", value)
        case Scalar.STRING:
            return None if isinstance(value, str) else _got("string", value)
        case Scalar.CHAR:
            return _char_problem(value)
        case Scalar.DECIMAL:
            return _decimal_problem(value, output)
        case Scalar.DATE:
            return _date_problem(value)


def _integer_problem(value: JsonValue, scalar: Scalar) -> str | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return _got(scalar.value, value)
    if scalar is Scalar.INT and not INT_MIN <= value <= INT_MAX:
        return f"{value} is outside the int range"
    if scalar is Scalar.LONG and abs(value) > MAX_SAFE_LONG:
        return f"{value} is beyond 2^53-1 (TypeScript number)"
    return None


def _char_problem(value: JsonValue) -> str | None:
    if not isinstance(value, str):
        return _got("char", value)
    if len(value) != 1:
        return _got("one character", value)
    if ord(value) >= BMP_LIMIT:
        return f"{value_text(value)} is outside the BMP"
    return None


def _decimal_problem(value: JsonValue, output: bool) -> str | None:
    if not isinstance(value, str):
        return f"{_got('decimal', value)} (decimals are JSON strings)"
    if DECIMAL_PATTERN.fullmatch(value) is None:
        return (
            f"{value_text(value)} is not a decimal (digits, an optional fraction, no leading zeros)"
        )
    if len(_decimal_digits(value)) > MAX_DECIMAL_DIGITS:
        return f"{value_text(value)} has more than {MAX_DECIMAL_DIGITS} significant digits"
    canonical = canonical_decimal(value)
    if output and value != canonical:
        return (
            f'{value_text(value)} is not canonical (no trailing fractional zeros, no "-0"): '
            f"write {value_text(canonical)}"
        )
    return None


def canonical_decimal(text: str) -> str:
    """The text a runner encodes the same number as: no trailing fractional zeros, no `-0`."""
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _decimal_digits(text: str) -> str:
    return text.removeprefix("-").replace(".", "").lstrip("0")


def _date_problem(value: JsonValue) -> str | None:
    if not isinstance(value, str):
        return _got("date", value)
    if DATE_PATTERN.fullmatch(value) is None:
        return f"{value_text(value)} is not a date (YYYY-MM-DD)"
    try:
        date.fromisoformat(value)
    except ValueError:
        return f"{value_text(value)} is not a calendar day (years 0001 to 9999)"
    return None


def _cyclic_list(value: dict[str, JsonValue], path: str) -> list[str]:
    values, cycle_at = value.get(CYCLE_VALUES), value.get(CYCLE_AT)
    if not isinstance(values, list):
        return [_issue(path, f'a cyclic list needs "{CYCLE_VALUES}": [...]')]
    issues = _Rules(output=False).issues(values, ArrayType(ScalarType(Scalar.INT)), path)
    is_index = (
        isinstance(cycle_at, int) and not isinstance(cycle_at, bool) and 0 <= cycle_at < len(values)
    )
    if not is_index:
        issues.append(_issue(path, f'"{CYCLE_AT}" must index into "{CYCLE_VALUES}"'))
    return issues


def _graph_node(value: JsonValue, path: str) -> list[str]:
    if not isinstance(value, list):
        return [_issue(path, _got("an adjacency list", value))]
    issues: list[str] = []
    for index, neighbors in enumerate(value):
        location = f"{path}[{index}]"
        if not isinstance(neighbors, list):
            issues.append(_issue(location, _got("an array", neighbors)))
            continue
        issues += [
            _issue(location, f"neighbor {value_text(neighbor)} is not a node (1..{len(value)})")
            for neighbor in neighbors
            if not isinstance(neighbor, int)
            or isinstance(neighbor, bool)
            or not 1 <= neighbor <= len(value)
        ]
    return issues


def _node_values(value: JsonValue, kind: NodeKind) -> set[JsonValue] | None:
    """The `val`s a `ref_of` parameter may name, or None when unknown."""
    if kind is NodeKind.GRAPH_NODE:
        return set(range(1, len(value) + 1)) if isinstance(value, list) else None
    if isinstance(value, dict):
        value = value.get(CYCLE_VALUES)
    if not isinstance(value, list):
        return None
    return {item for item in value if isinstance(item, int)}


def _function_case(signature: FunctionSignature, case: Case) -> list[str]:
    if isinstance(case.input, OperationSequence):
        return ["a function problem's cases need input, not ops"]
    if not isinstance(case.input, FunctionInput):
        return []
    issues = _argument_issues(signature.params, case.input.arguments)
    if case.expected is not None:
        issues += _returns_issues(case.expected.value, signature, "expected")
    return issues


def _argument_issues(params: tuple[Param, ...], arguments: Mapping[str, JsonValue]) -> list[str]:
    names = [param.name for param in params]
    issues = [f'input: missing "{name}"' for name in names if name not in arguments]
    issues += [f'input: unknown parameter "{name}"' for name in arguments if name not in names]
    inputs = _Rules(output=False)
    for param in params:
        if param.name not in arguments:
            continue
        path = f"input.{param.name}"
        if param.ref_of is None:
            issues += inputs.issues(arguments[param.name], param.type, path)
        else:
            issues += _ref_of_issues(param, arguments, path)
    return issues


def _ref_of_issues(param: Param, arguments: Mapping[str, JsonValue], path: str) -> list[str]:
    """A `ref_of` parameter holds the `val` of a node in the referenced parameter."""
    value = arguments[param.name]
    problem = _integer_problem(value, Scalar.INT)
    if problem is not None:
        return [_issue(path, problem)]
    if param.ref_of is None or not isinstance(param.type, NodeType):
        return []
    known = _node_values(arguments.get(param.ref_of), param.type.kind)
    if known is None or value in known:
        return []
    return [_issue(path, f"{value_text(value)} is not a value in {param.ref_of}")]


def _returns_issues(value: JsonValue, member: FunctionSignature | Method, path: str) -> list[str]:
    returns = member.returns
    if isinstance(returns.type, VoidType):
        if returns.output_from is not None:
            source = next(param for param in member.params if param.name == returns.output_from)
            return _Rules(output=True).issues(value, source.type, path)
        return [] if value is None else [_issue(path, "void returns expect null")]
    match returns.serialize_as:
        case NodeSerialization.VALUE:
            valid = value is None or not _integer_problem(value, Scalar.INT)
            return [] if valid else [_issue(path, _got("int or null", value))]
        case NodeSerialization.INDEX:
            valid = not _integer_problem(value, Scalar.INT)
            return [] if valid else [_issue(path, _got("an index", value))]
        case None:
            return _Rules(output=True).issues(value, returns.type, path)


def _class_case(signature: ClassSignature, case: Case) -> list[str]:
    if isinstance(case.input, FunctionInput):
        return ["a class problem's cases need ops and args, not input"]
    if not isinstance(case.input, OperationSequence):
        return []
    sequence = case.input
    methods = {method.name: method for method in signature.methods}
    issues = _operation_issues(signature, sequence, methods)
    if case.expected is not None:
        issues += _expected_outputs_issues(case.expected.value, sequence, methods)
    return issues


def _operation_issues(
    signature: ClassSignature, sequence: OperationSequence, methods: dict[str, Method]
) -> list[str]:
    issues: list[str] = []
    for index, (operation, arguments) in enumerate(zip(sequence.ops, sequence.args, strict=False)):
        if index == 0:
            if operation != signature.name:
                issues.append(f'ops[0]: expected the class name "{signature.name}"')
                continue
            params, label = signature.constructor_params, signature.name
        elif operation in methods:
            params, label = methods[operation].params, operation
        else:
            issues.append(f'ops[{index}]: no method "{operation}"')
            continue
        issues += _arguments_issues(params, arguments, f"args[{index}]", label)
    return issues


def _arguments_issues(
    params: tuple[Param, ...], arguments: tuple[JsonValue, ...], path: str, label: str
) -> list[str]:
    if len(arguments) != len(params):
        noun = "argument" if len(params) == 1 else "arguments"
        return [f"{path}: {label} takes {len(params)} {noun}, got {len(arguments)}"]
    inputs = _Rules(output=False)
    return [
        issue
        for position, (param, argument) in enumerate(zip(params, arguments, strict=True))
        for issue in inputs.issues(argument, param.type, f"{path}[{position}]")
    ]


def _expected_outputs_issues(
    expected: JsonValue, sequence: OperationSequence, methods: dict[str, Method]
) -> list[str]:
    if not isinstance(expected, list):
        return [_issue("expected", _got("an array", expected))]
    if len(expected) != len(sequence.ops):
        return [f"expected: {len(expected)} values for {len(sequence.ops)} operations"]
    issues: list[str] = []
    if expected and expected[0] is not None:
        issues.append("expected[0]: the constructor expects null")
    for index, (operation, value) in enumerate(zip(sequence.ops, expected, strict=True)):
        if index and operation in methods:
            issues += _returns_issues(value, methods[operation], f"expected[{index}]")
    return issues
