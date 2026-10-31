"""`kotlinc` output, as Gradle prints it, as structured diagnostics: the `DiagnosticParser` for
Kotlin builds (docs/specs/cli.md#diagnostics).

Each diagnostic is one line, `e: file:///ws/src/Bank.kt:12:5 <message>`, with `w:` for a warning
and `i:` for information, or without the place for a problem with the build itself. Indented
lines below it continue the message. Kotlin names no code for a problem.
"""

import re
from dataclasses import dataclass, replace

from coding_study.domain.diagnostics import (
    Diagnostic,
    DiagnosticSource,
    Severity,
    named_file,
)

KOTLINC_DIAGNOSTIC = re.compile(
    r"(?P<level>[ewi]): (?:(?P<file>\S.*?):(?P<line>\d+):(?P<column>\d+) )?(?P<message>.*)"
)
SEVERITIES = {"e": Severity.ERROR, "w": Severity.WARNING, "i": Severity.INFO}
CONTINUATION_PREFIXES = (" ", "\t")


@dataclass(frozen=True, slots=True)
class KotlincReport:
    def parse(self, output: str) -> tuple[Diagnostic, ...]:
        """Every diagnostic in `output`, in `kotlinc`'s order; other lines are left out."""
        diagnostics: list[Diagnostic] = []
        for line in output.splitlines():
            found = KOTLINC_DIAGNOSTIC.fullmatch(line)
            if found is not None:
                diagnostics.append(_diagnostic(found))
            elif diagnostics and line.startswith(CONTINUATION_PREFIXES):
                last = diagnostics[-1]
                diagnostics[-1] = replace(last, message=f"{last.message}\n{line}")
        return tuple(diagnostics)


def _diagnostic(found: re.Match[str]) -> Diagnostic:
    placed = found["file"] is not None
    return Diagnostic(
        message=found["message"],
        source=DiagnosticSource.BUILD,
        severity=SEVERITIES[found["level"]],
        file=named_file(found["file"]) if placed else None,
        line=int(found["line"]) if placed else None,
        column=int(found["column"]) if placed else None,
    )
