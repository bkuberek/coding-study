"""`tsc --pretty false` output as structured diagnostics: the `DiagnosticParser` for TypeScript's
type check (docs/specs/cli.md#diagnostics).

`tsc` writes one diagnostic per line, `src/bank.ts(3,5): error TS2322: <message>`, or without the
place for a problem with the project itself, and continues a message on the lines below it,
indented. Its paths are relative to the directory it ran in.
"""

import re
from dataclasses import dataclass, replace

from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity

TSC_DIAGNOSTIC = re.compile(
    r"(?:(?P<file>.+)\((?P<line>\d+),(?P<column>\d+)\): )?"
    r"(?P<category>error|warning|message|suggestion) (?P<code>TS\d+): (?P<message>.*)"
)
SEVERITIES = {
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "message": Severity.INFO,
    "suggestion": Severity.INFO,
}
"""tsc's diagnostic categories."""
CONTINUATION_PREFIXES = (" ", "\t")
PARENT = "../"
SEPARATOR = "/"


@dataclass(frozen=True, slots=True)
class TscReport:
    folder: str
    """The project folder, relative to the directory whose paths tsc's output uses."""

    def parse(self, output: str) -> tuple[Diagnostic, ...]:
        """Every diagnostic in `output`, in tsc's order; other lines are left out."""
        diagnostics: list[Diagnostic] = []
        for line in output.splitlines():
            found = TSC_DIAGNOSTIC.fullmatch(line)
            if found is not None:
                diagnostics.append(self._diagnostic(found))
            elif diagnostics and line.startswith(CONTINUATION_PREFIXES):
                last = diagnostics[-1]
                diagnostics[-1] = replace(last, message=f"{last.message}\n{line}")
        return tuple(diagnostics)

    def _diagnostic(self, found: re.Match[str]) -> Diagnostic:
        placed = found["file"] is not None
        return Diagnostic(
            message=found["message"],
            source=DiagnosticSource.TYPECHECK,
            severity=SEVERITIES[found["category"]],
            file=self._from_folder(found["file"]) if placed else None,
            line=int(found["line"]) if placed else None,
            column=int(found["column"]) if placed else None,
            code=found["code"],
        )

    def _from_folder(self, path: str) -> str:
        """`path` relative to the project folder, climbing out of it for a file elsewhere."""
        inside = f"{self.folder}{SEPARATOR}"
        if path.startswith(inside):
            return path.removeprefix(inside)
        return f"{PARENT * (self.folder.count(SEPARATOR) + 1)}{path}"
