"""`javac` output as structured diagnostics: the `DiagnosticParser` for Java builds
(docs/specs/cli.md#diagnostics).

`javac` writes `src/Bank.java:12: error: <message>`, then the source line, a caret line whose
caret stands under the column, and the rest of the message indented below it (`symbol:` and
`location:` for an unresolved name). A warning has the same shape, with a lint category such as
`[removal]` before its message. A `Note:` line is a message of its own, which may name a file.
Gradle prints the paths as `javac` is given them, absolute.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from coding_study.domain.diagnostics import (
    Diagnostic,
    DiagnosticSource,
    Severity,
    named_file,
)

JAVAC_DIAGNOSTIC = re.compile(
    r"(?:(?P<file>\S.*?\.java):(?P<line>\d+): )?(?P<category>error|warning): (?P<message>.*)"
)
JAVAC_NOTE = re.compile(r"Note: (?:(?P<file>\S+\.java) )?(?P<message>.*)")
LINT_CATEGORY = re.compile(r"\[(?P<category>[\w-]+)\] (?P<message>.*)", re.DOTALL)
CARET_LINE = re.compile(r"[ \t]*\^[ \t]*")
CARET = "^"
SEVERITIES = {"error": Severity.ERROR, "warning": Severity.WARNING}
CONTINUATION_PREFIXES = (" ", "\t")


@dataclass(frozen=True, slots=True)
class JavacReport:
    def parse(self, output: str) -> tuple[Diagnostic, ...]:
        """Every error, warning and note in `output`, in `javac`'s order; other lines are left
        out."""
        lines = output.splitlines()
        diagnostics: list[Diagnostic] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            index += 1
            found = JAVAC_DIAGNOSTIC.fullmatch(line)
            note = JAVAC_NOTE.fullmatch(line)
            if found is not None:
                column, index = _caret_column(lines, index) if found["file"] else (None, index)
                details, index = _details(lines, index)
                diagnostics.append(_diagnostic(found, column, details))
            elif note is not None:
                diagnostics.append(_note(note))
        return tuple(diagnostics)


def _caret_column(lines: Sequence[str], index: int) -> tuple[int | None, int]:
    """The column of the caret line that follows the source line at `index`, and the index past
    both lines; no column and `index` unchanged when the line is not followed by a caret line."""
    caret = lines[index + 1] if index + 1 < len(lines) else ""
    if CARET_LINE.fullmatch(caret) is None:
        return None, index
    return caret.index(CARET) + 1, index + 2


def _details(lines: Sequence[str], index: int) -> tuple[list[str], int]:
    """The indented lines that finish a message."""
    start = index
    while index < len(lines) and lines[index].startswith(CONTINUATION_PREFIXES):
        index += 1
    return list(lines[start:index]), index


def _diagnostic(found: re.Match[str], column: int | None, details: list[str]) -> Diagnostic:
    lint = LINT_CATEGORY.fullmatch(found["message"])
    placed = found["file"] is not None
    return Diagnostic(
        message="\n".join([lint["message"] if lint else found["message"], *details]),
        source=DiagnosticSource.BUILD,
        severity=SEVERITIES[found["category"]],
        file=named_file(found["file"]) if placed else None,
        line=int(found["line"]) if placed else None,
        column=column,
        code=lint["category"] if lint else None,
    )


def _note(found: re.Match[str]) -> Diagnostic:
    file = found["file"]
    return Diagnostic(
        message=found["message"],
        source=DiagnosticSource.BUILD,
        severity=Severity.INFO,
        file=named_file(file) if file else None,
    )
