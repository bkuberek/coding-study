"""The Rust runner's report of compiler errors as structured diagnostics: the `DiagnosticParser`
for Rust builds (docs/specs/cli.md#diagnostics).

The runner builds with `cargo build --message-format=json`, reads rustc's messages, and reports
each as `src/bank.rs:12:5: error[E0599]: <message>`: the primary span's place, the error code in
brackets, then the span's label and the `note:` and `help:` lines of its children, indented. A
line of a note that wraps follows without indentation. A diagnostic runs to the next one.
"""

import re
from dataclasses import dataclass, replace

from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity

RUSTC_DIAGNOSTIC = re.compile(
    r"(?P<file>\S.*?):(?P<line>\d+):(?P<column>\d+): "
    r"(?P<category>error|warning)(?:\[(?P<code>\w+)\])?: (?P<message>.*)"
)
SEVERITIES = {"error": Severity.ERROR, "warning": Severity.WARNING}


@dataclass(frozen=True, slots=True)
class RustcReport:
    def parse(self, output: str) -> tuple[Diagnostic, ...]:
        """Every diagnostic in `output`, in the order rustc reported them; lines before the first
        are left out."""
        diagnostics: list[Diagnostic] = []
        for line in output.splitlines():
            found = RUSTC_DIAGNOSTIC.fullmatch(line)
            if found is not None:
                diagnostics.append(_diagnostic(found))
            elif diagnostics:
                last = diagnostics[-1]
                diagnostics[-1] = replace(last, message=f"{last.message}\n{line}")
        return tuple(diagnostics)


def _diagnostic(found: re.Match[str]) -> Diagnostic:
    return Diagnostic(
        message=found["message"],
        source=DiagnosticSource.BUILD,
        severity=SEVERITIES[found["category"]],
        file=found["file"],
        line=int(found["line"]),
        column=int(found["column"]),
        code=found["code"],
    )
