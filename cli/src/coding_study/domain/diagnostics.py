"""Structured diagnostics: where a project's code fails to load, build or type-check
(docs/specs/cli.md#diagnostics).

A runner reports code that does not load as an error whose trace lists frames as `file:line` or
`file:line in function`, innermost last (docs/specs/runners.md#event-stream---out-json-lines); the
innermost frame is where the problem is. A type checker or a compiler reports in a format of its
own, which a `DiagnosticParser` for that tool turns into the same shape.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from coding_study.domain.runs import UserError

TRACE_FRAME = re.compile(r"(?P<file>.+):(?P<line>\d+)(?: in .+)?")
"""One frame of a runner's trace: `bank/bank.py:12 in Bank.deposit`, or `bank/bank.py:5`."""


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticSource(StrEnum):
    LOAD = "load"
    """The runner could not load the code, or the framework could not collect a test file."""
    TYPECHECK = "typecheck"
    """A type checker, such as `tsc --noEmit` for `cstudy test --typecheck`."""
    BUILD = "build"
    """A compiler."""


@dataclass(frozen=True, slots=True)
class Diagnostic:
    message: str
    source: DiagnosticSource
    severity: Severity = Severity.ERROR
    file: str | None = None
    """Relative to the project folder; None when the report names no file."""
    line: int | None = None
    """1-based; None when the report names no line."""
    column: int | None = None
    """1-based; None when the report names no column, as a runner's trace never does."""
    code: str | None = None
    """The tool's name for the problem: an exception type (`SyntaxError`) or a compiler's code
    (`TS2322`)."""


class DiagnosticParser(Protocol):
    """Reads one tool's report, such as `tsc --pretty false` output, into diagnostics."""

    def parse(self, output: str) -> tuple[Diagnostic, ...]:
        """Every diagnostic in `output`, in the order the tool reported them, with paths relative
        to the project folder."""
        ...


def load_diagnostic(error: UserError) -> Diagnostic:
    """Code that did not load, at the innermost frame of its trace when that frame names a place."""
    frames = error.trace.splitlines()
    place = TRACE_FRAME.fullmatch(frames[-1]) if frames else None
    return Diagnostic(
        message=error.message or error.type,
        source=DiagnosticSource.LOAD,
        file=place["file"] if place else None,
        line=int(place["line"]) if place else None,
        code=error.type,
    )


def distinct(diagnostics: Iterable[Diagnostic]) -> tuple[Diagnostic, ...]:
    """Each diagnostic once, where it first appears: files that import one broken module all
    fail on its line."""
    return tuple(dict.fromkeys(diagnostics))
