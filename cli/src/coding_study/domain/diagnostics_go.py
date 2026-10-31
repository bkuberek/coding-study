"""`go build` and `go vet` output as structured diagnostics: the `DiagnosticParser` for Go builds
(docs/specs/cli.md#diagnostics).

The `go` command writes `go/practice/two_sum/two_sum.go:14:14: undefined: x` for each problem in
a file, or `two_sum.go:3: ...` without the column, and continues a message on the lines below it,
indented with a tab (`have (...)`, `want (...)`). A `# package` line names the package the lines
below belong to, and `go vet` names its type-check errors as `vet: ./two_sum.go:7:17: ...`.
Paths are relative to the directory the command ran in, with `./` before a file in it.
"""

import re
from dataclasses import dataclass, replace

from coding_study.domain.diagnostics import (
    Diagnostic,
    DiagnosticSource,
    Severity,
    named_file,
)

GO_DIAGNOSTIC = re.compile(
    r"(?:vet: )?(?P<file>[^\s:][^:]*\.go):(?P<line>\d+)(?::(?P<column>\d+))?: (?P<message>.*)"
)
CONTINUATION_PREFIXES = (" ", "\t")


@dataclass(frozen=True, slots=True)
class GoReport:
    def parse(self, output: str) -> tuple[Diagnostic, ...]:
        """Every diagnostic in `output`, in the order `go` reported them; other lines are left
        out."""
        diagnostics: list[Diagnostic] = []
        for line in output.splitlines():
            found = GO_DIAGNOSTIC.fullmatch(line)
            if found is not None:
                diagnostics.append(_diagnostic(found))
            elif diagnostics and line.startswith(CONTINUATION_PREFIXES):
                last = diagnostics[-1]
                diagnostics[-1] = replace(last, message=f"{last.message}\n{line}")
        return tuple(diagnostics)


def _diagnostic(found: re.Match[str]) -> Diagnostic:
    column = found["column"]
    return Diagnostic(
        message=found["message"],
        source=DiagnosticSource.BUILD,
        severity=Severity.ERROR,
        file=named_file(found["file"]),
        line=int(found["line"]),
        column=int(column) if column else None,
    )
