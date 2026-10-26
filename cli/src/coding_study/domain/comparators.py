"""Judging a runner's output against the expected value (docs/specs/problem-format.md#comparators).

All comparison happens here, on canonical JSON values. Equality is type-strict for booleans
(`true` never equals `1`); integers and floats compare by numeric value.
"""

from collections import Counter
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from coding_study.domain.cases import Expected, FunctionInput, JsonValue, OperationSequence
from coding_study.domain.problem import ComparatorSpec, ComparatorType
from coding_study.domain.runs import RunInput
from coding_study.domain.value_text import value_text

type Checker = Callable[[dict[str, JsonValue], JsonValue, JsonValue | None], str | None]
"""`check(case_input, output, expected)` from a problem's checker.py: None accepts the output,
otherwise a one-line reason."""

type _NumbersEqual = Callable[[int | float, int | float], bool]


@dataclass(frozen=True, slots=True)
class Mismatch:
    """Why an output was rejected; an empty `detail` means expected and actual say it all."""

    detail: str | None = None
    first_difference: int | None = None
    """For arrays: the first index (or operation) whose value differs."""


class Comparator(Protocol):
    @property
    def label(self) -> str | None:
        """Shown after the expected value in failure reports, e.g. "unordered"."""
        ...

    def compare(
        self, expected: Expected | None, actual: JsonValue, case_input: RunInput
    ) -> Mismatch | None:
        """None when `actual` is accepted."""
        ...


def comparator_for(spec: ComparatorSpec, checker: Checker | None = None) -> Comparator:
    """`checker` is required, and only used, when `spec.type` is `checker`."""
    match spec.type:
        case ComparatorType.CHECKER:
            if checker is None:
                raise ValueError("a checker comparator needs the problem's checker")
            return CheckerComparator(checker)
        case ComparatorType.OPS:
            return OpsComparator(spec)
        case _:
            return _value_comparator(spec.type, spec.tolerance)


def _value_comparator(comparator_type: ComparatorType, tolerance: float) -> Comparator:
    match comparator_type:
        case ComparatorType.UNORDERED:
            return MultisetComparator(canonical_key, "unordered")
        case ComparatorType.UNORDERED_NESTED:
            return MultisetComparator(_nested_multiset_key, "unordered-nested")
        case ComparatorType.FLOAT:
            return StructuralComparator(_within(tolerance), f"float, tolerance {tolerance:g}")
        case ComparatorType.EXACT:
            return StructuralComparator(_numerically_equal, None)
        case _:
            raise ValueError(f'"{comparator_type}" cannot compare single values')


def _required(expected: Expected | None) -> JsonValue:
    if expected is None:
        raise ValueError("this comparator needs an expected value")
    return expected.value


class StructuralComparator:
    """`exact` and `float`: deep equality where only the number comparison differs."""

    def __init__(self, numbers_equal: _NumbersEqual, label: str | None) -> None:
        self._numbers_equal = numbers_equal
        self._label = label

    @property
    def label(self) -> str | None:
        return self._label

    def compare(
        self, expected: Expected | None, actual: JsonValue, case_input: RunInput
    ) -> Mismatch | None:
        expected_value = _required(expected)
        if isinstance(expected_value, list) and isinstance(actual, list):
            return self._compare_arrays(expected_value, actual)
        return None if self.equal(expected_value, actual) else Mismatch()

    def equal(self, expected: JsonValue, actual: JsonValue) -> bool:
        if isinstance(expected, bool) or isinstance(actual, bool):
            return type(expected) is type(actual) and expected == actual
        if isinstance(expected, int | float) and isinstance(actual, int | float):
            return self._numbers_equal(expected, actual)
        if isinstance(expected, list) and isinstance(actual, list):
            return len(expected) == len(actual) and all(map(self.equal, expected, actual))
        if isinstance(expected, dict) and isinstance(actual, dict):
            return expected.keys() == actual.keys() and all(
                self.equal(value, actual[key]) for key, value in expected.items()
            )
        return type(expected) is type(actual) and expected == actual

    def _compare_arrays(
        self, expected: Sequence[JsonValue], actual: Sequence[JsonValue]
    ) -> Mismatch | None:
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual, strict=False)):
            if not self.equal(expected_item, actual_item):
                return Mismatch(f"first difference at index {index}", first_difference=index)
        if len(expected) != len(actual):
            detail = f"{len(actual)} elements, expected {len(expected)}"
            return Mismatch(detail, first_difference=min(len(expected), len(actual)))
        return None


def _numerically_equal(expected: int | float, actual: int | float) -> bool:
    return expected == actual


def _within(tolerance: float) -> _NumbersEqual:
    def numbers_equal(expected: int | float, actual: int | float) -> bool:
        return abs(actual - expected) <= tolerance * max(1, abs(expected))

    return numbers_equal


class MultisetComparator:
    """`unordered` and `unordered-nested`: top-level arrays compared as multisets of keys."""

    def __init__(self, key: Callable[[JsonValue], Hashable], label: str) -> None:
        self._key = key
        self._label = label

    @property
    def label(self) -> str | None:
        return self._label

    def compare(
        self, expected: Expected | None, actual: JsonValue, case_input: RunInput
    ) -> Mismatch | None:
        expected_value = _required(expected)
        if not isinstance(actual, list) or not isinstance(expected_value, list):
            return Mismatch("expected an array")
        if Counter(map(self._key, expected_value)) == Counter(map(self._key, actual)):
            return None
        return Mismatch()


def canonical_key(value: JsonValue) -> Hashable:
    """Equal keys exactly when `exact` considers the values equal (1 and 1.0 share a key)."""
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int | float):
        return ("number", value)
    if isinstance(value, list):
        return ("array", tuple(map(canonical_key, value)))
    if isinstance(value, dict):
        return ("object", frozenset((key, canonical_key(item)) for key, item in value.items()))
    return (type(value).__name__, value)


def _nested_multiset_key(value: JsonValue) -> Hashable:
    if isinstance(value, list):
        return ("multiset", frozenset(Counter(map(canonical_key, value)).items()))
    return canonical_key(value)


class CheckerComparator:
    """`checker`: the problem's checker.py validates the answer itself."""

    def __init__(self, checker: Checker) -> None:
        self._checker = checker

    @property
    def label(self) -> str | None:
        return "checker"

    def compare(
        self, expected: Expected | None, actual: JsonValue, case_input: RunInput
    ) -> Mismatch | None:
        expected_value = expected.value if expected is not None else None
        try:
            reason = self._checker(_checker_input(case_input), actual, expected_value)
        except Exception as error:  # content code: any failure rejects the output
            return Mismatch(f"checker raised {type(error).__name__}: {error}")
        return None if reason is None else Mismatch(reason)


def _checker_input(case_input: RunInput) -> dict[str, JsonValue]:
    if isinstance(case_input, FunctionInput):
        return dict(case_input.arguments)
    return {
        "ops": list(case_input.ops),
        "args": [list(arguments) for arguments in case_input.args],
    }


class OpsComparator:
    """`ops`: one output per operation; `per_method` overrides a method's comparator."""

    def __init__(self, spec: ComparatorSpec) -> None:
        self._exact = _value_comparator(ComparatorType.EXACT, spec.tolerance)
        self._per_method: Mapping[str, Comparator] = {
            method: _value_comparator(comparator_type, spec.tolerance)
            for method, comparator_type in spec.per_method.items()
        }

    @property
    def label(self) -> str | None:
        return None

    def compare(
        self, expected: Expected | None, actual: JsonValue, case_input: RunInput
    ) -> Mismatch | None:
        if not isinstance(case_input, OperationSequence):
            raise ValueError("the ops comparator needs an operation sequence")
        expected_outputs = _required(expected)
        if not isinstance(actual, list) or not isinstance(expected_outputs, list):
            return Mismatch("expected an array")
        if len(actual) != len(expected_outputs):
            return Mismatch(f"{len(actual)} outputs for {len(expected_outputs)} operations")
        outputs = zip(case_input.ops, expected_outputs, actual, strict=False)
        for index, (operation, expected_output, actual_output) in enumerate(outputs):
            comparator = self._per_method.get(operation, self._exact)
            if comparator.compare(Expected(expected_output), actual_output, _NO_INPUT) is not None:
                detail = (
                    f"op {index} {operation}: "
                    f"expected {value_text(expected_output)}, got {value_text(actual_output)}"
                )
                return Mismatch(detail, first_difference=index)
        return None


_NO_INPUT = FunctionInput({})
