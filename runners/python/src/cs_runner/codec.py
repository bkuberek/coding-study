"""Case inputs from JSON and return values to JSON, driven by the declared type
(docs/specs/problem-format.md#type-mapping).

Decoding trusts content validated by the CLI but still rejects a value of the wrong shape with
CaseInputError. Encoding is strict: a value that does not fit its declared type is
`invalid_output`, with the position of the offending element.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeIs, cast

from cs_runner.dsl import NodeType, Scalar, ScalarType, SequenceType, ValueType
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.json_value import Json, is_int, type_name
from cs_runner.nodes import NODE_BUILDERS, NODE_ENCODERS

INT_BITS = 31
SAFE_INTEGER_BITS = 53
"""`long` values stay within 2^53 - 1 so TypeScript numbers represent them exactly."""
MAX_BMP_CODE_POINT = 0xFFFF


def decode(value: Json, value_type: ValueType) -> object:
    match value_type:
        case ScalarType(scalar):
            return _SCALAR_DECODERS[scalar](value)
        case NodeType(kind):
            return NODE_BUILDERS[kind](value)
        case SequenceType(element):
            if not isinstance(value, list):
                raise CaseInputError(f"expected an array, got {value!r}")
            return [decode(item, element) for item in value]


def encode(value: object, value_type: ValueType, location: str = "") -> Json:
    """`location` prefixes the reason of an invalid output, e.g. `[2][0]: expected int`."""
    if isinstance(value_type, SequenceType):
        return _encode_sequence(value, value_type.element, location)
    try:
        if isinstance(value_type, ScalarType):
            return _SCALAR_ENCODERS[value_type.scalar](value)
        return NODE_ENCODERS[value_type.kind](value)
    except InvalidOutputError as error:
        if not location:
            raise
        raise InvalidOutputError(f"{location}: {error.reason}") from None


def _encode_sequence(value: object, element: ValueType, location: str) -> list[Json]:
    if not isinstance(value, list | tuple):
        raise InvalidOutputError(_located(location, _mismatch("a list", value)))
    items = cast("Sequence[object]", value)
    return [encode(item, element, f"{location}[{index}]") for index, item in enumerate(items)]


@dataclass(frozen=True, slots=True)
class _IntegerRange:
    name: str
    lowest: int
    highest: int

    def decode(self, value: Json) -> int:
        if not is_int(value):
            raise CaseInputError(_mismatch(self.name, value))
        return value

    def encode(self, value: object) -> int:
        if not is_int(value):
            raise InvalidOutputError(_mismatch(self.name, value))
        if not self.lowest <= value <= self.highest:
            raise InvalidOutputError(f"{self.name} out of range: {value}")
        return value


_INT = _IntegerRange(Scalar.INT, -(2**INT_BITS), 2**INT_BITS - 1)
_LONG = _IntegerRange(Scalar.LONG, -(2**SAFE_INTEGER_BITS - 1), 2**SAFE_INTEGER_BITS - 1)


def _decode_double(value: Json) -> float:
    if is_int(value) or isinstance(value, float):
        return float(value)
    raise CaseInputError(_mismatch(Scalar.DOUBLE, value))


def _encode_double(value: object) -> float:
    if not (is_int(value) or isinstance(value, float)):
        raise InvalidOutputError(_mismatch(Scalar.DOUBLE, value))
    try:
        number = float(value)
    except OverflowError:
        raise InvalidOutputError(f"double out of range: {value}") from None
    if not math.isfinite(number):
        raise InvalidOutputError(f"non-finite double: {number}")
    return number


def _decode_bool(value: Json) -> bool:
    if not isinstance(value, bool):
        raise CaseInputError(_mismatch(Scalar.BOOL, value))
    return value


def _encode_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise InvalidOutputError(_mismatch(Scalar.BOOL, value))
    return value


def _decode_string(value: Json) -> str:
    if not isinstance(value, str):
        raise CaseInputError(_mismatch(Scalar.STRING, value))
    return value


def _encode_string(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidOutputError(_mismatch(Scalar.STRING, value))
    return value


def _decode_char(value: Json) -> str:
    if not _is_char(value):
        raise CaseInputError(_char_mismatch(value))
    return value


def _encode_char(value: object) -> str:
    if not _is_char(value):
        raise InvalidOutputError(_char_mismatch(value))
    return value


def _is_char(value: object) -> TypeIs[str]:
    return isinstance(value, str) and len(value) == 1 and ord(value) <= MAX_BMP_CODE_POINT


def _char_mismatch(value: object) -> str:
    if isinstance(value, str):
        return f"expected char, got a string of length {len(value)}: {value!r}"
    return _mismatch(Scalar.CHAR, value)


def _mismatch(expected: str, value: object) -> str:
    return f"expected {expected}, got {type_name(value)}"


def _located(location: str, reason: str) -> str:
    return f"{location}: {reason}" if location else reason


_SCALAR_DECODERS: Mapping[Scalar, Callable[[Json], object]] = {
    Scalar.INT: _INT.decode,
    Scalar.LONG: _LONG.decode,
    Scalar.DOUBLE: _decode_double,
    Scalar.BOOL: _decode_bool,
    Scalar.STRING: _decode_string,
    Scalar.CHAR: _decode_char,
}
_SCALAR_ENCODERS: Mapping[Scalar, Callable[[object], Json]] = {
    Scalar.INT: _INT.encode,
    Scalar.LONG: _LONG.encode,
    Scalar.DOUBLE: _encode_double,
    Scalar.BOOL: _encode_bool,
    Scalar.STRING: _encode_string,
    Scalar.CHAR: _encode_char,
}
