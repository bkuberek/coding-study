"""Java and Kotlin columns of the type mapping (docs/specs/problem-format.md#type-mapping).

Every Kotlin type erases to the same JVM type as its Java counterpart, so one JVM runner serves
both languages.
"""

from collections.abc import Mapping

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

JAVA_VOID = "void"

_JAVA_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "int",
    Scalar.LONG: "long",
    Scalar.DOUBLE: "double",
    Scalar.BOOL: "boolean",
    Scalar.STRING: "String",
    Scalar.CHAR: "char",
    Scalar.DECIMAL: "BigDecimal",
    Scalar.DATE: "LocalDate",
}
_JAVA_BOXED: Mapping[Scalar, str] = {
    Scalar.INT: "Integer",
    Scalar.LONG: "Long",
    Scalar.DOUBLE: "Double",
    Scalar.BOOL: "Boolean",
    Scalar.STRING: "String",
    Scalar.CHAR: "Character",
    Scalar.DECIMAL: "BigDecimal",
    Scalar.DATE: "LocalDate",
}
_KOTLIN_SCALARS: Mapping[Scalar, str] = {
    Scalar.INT: "Int",
    Scalar.LONG: "Long",
    Scalar.DOUBLE: "Double",
    Scalar.BOOL: "Boolean",
    Scalar.STRING: "String",
    Scalar.CHAR: "Char",
    Scalar.DECIMAL: "BigDecimal",
    Scalar.DATE: "LocalDate",
}
_KOTLIN_PRIMITIVE_ARRAYS: Mapping[Scalar, str] = {
    Scalar.INT: "IntArray",
    Scalar.LONG: "LongArray",
    Scalar.DOUBLE: "DoubleArray",
    Scalar.BOOL: "BooleanArray",
    Scalar.CHAR: "CharArray",
}


def java_type(value_type: ValueType) -> str:
    match value_type:
        case ScalarType(scalar):
            return _JAVA_SCALARS[scalar]
        case NodeType(kind):
            return kind.value
        case ArrayType(element):
            return f"{java_type(element)}[]"
        case ListType(element):
            return f"List<{_java_type_argument(element)}>"


def java_return_type(return_type: ReturnType) -> str:
    if isinstance(return_type, VoidType):
        return JAVA_VOID
    return java_type(return_type)


def kotlin_type(value_type: ValueType) -> str:
    """Node types are nullable; primitive arrays use Kotlin's specialized array classes."""
    match value_type:
        case ScalarType(scalar):
            return _KOTLIN_SCALARS[scalar]
        case NodeType(kind):
            return f"{kind.value}?"
        case ArrayType(ScalarType(scalar)) if scalar in _KOTLIN_PRIMITIVE_ARRAYS:
            return _KOTLIN_PRIMITIVE_ARRAYS[scalar]
        case ArrayType(element):
            return f"Array<{kotlin_type(element)}>"
        case ListType(element):
            return f"List<{kotlin_type(element)}>"


def kotlin_return_type(return_type: ReturnType) -> str | None:
    """None for `void`: Kotlin functions returning Unit omit the return type."""
    if isinstance(return_type, VoidType):
        return None
    return kotlin_type(return_type)


def _java_type_argument(value_type: ValueType) -> str:
    if isinstance(value_type, ScalarType):
        return _JAVA_BOXED[value_type.scalar]
    return java_type(value_type)
