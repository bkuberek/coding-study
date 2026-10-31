"""Structured diagnostics as JSON values (docs/specs/cli.md#diagnostics)."""

from coding_study.domain.cases import JsonValue
from coding_study.domain.diagnostics import Diagnostic


def diagnostic_value(diagnostic: Diagnostic) -> dict[str, JsonValue]:
    """Every field, null when the report names none."""
    return {
        "source": diagnostic.source.value,
        "severity": diagnostic.severity.value,
        "file": diagnostic.file,
        "line": diagnostic.line,
        "column": diagnostic.column,
        "code": diagnostic.code,
        "message": diagnostic.message,
    }
