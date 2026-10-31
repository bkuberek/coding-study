"""Structured diagnostics: where a project's code fails to load, build or type-check
(docs/specs/cli.md#diagnostics).

A runner reports code that does not load as an error whose trace lists frames as `file:line` or
`file:line in function`, innermost last (docs/specs/runners.md#event-stream---out-json-lines); the
innermost frame is where the problem is. A framework that refuses to run a suite reports in its own
words instead, which for pytest hold a Python traceback with absolute paths. A type checker or a
compiler reports in a format of its own, which a `DiagnosticParser` for that tool turns into the
same shape.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

from coding_study.domain.runs import UserError

TRACE_FRAME = re.compile(r"(?P<file>.+):(?P<line>\d+)(?: in .+)?")
"""One frame of a runner's trace: `bank/bank.py:12 in Bank.deposit`, or `bank/bank.py:5`."""
PYTHON_FILE_FRAME = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)')
"""A frame of a Python traceback: `File "/ws/projects/bank/bank/bank.py", line 3`."""
PYTHON_SHORT_FRAME = re.compile(r"(?P<file>[^\s:]+):(?P<line>\d+): in ")
"""A frame of pytest's short traceback, relative to its root when inside it:
`bank/bank.py:3: in <module>`."""
PYTHON_EXCEPTION = re.compile(r"(?:E\s+)?(?P<type>[A-Z]\w*(?:Error|Exception)): (?P<message>.*)")
"""The last line of a Python traceback, behind pytest's `E` gutter: `E   SyntaxError: invalid
syntax`."""
ABSOLUTE_PREFIX = "/"
PARENT_PREFIX = "../"
PATH_SEPARATOR = "/"


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


def report_diagnostic(error: UserError, root: str) -> Diagnostic:
    """Code that did not load, read from a framework's own report of it: the innermost frame in
    the project folder `root` and the last exception of a Python traceback, as pytest prints one
    when a `conftest.py` does not import. Without them, the error as it is."""
    lines = error.message.splitlines()
    place = _innermost_place(lines, root)
    exception = _last_exception(lines)
    return Diagnostic(
        message=exception["message"] if exception else error.message or error.type,
        source=DiagnosticSource.LOAD,
        file=place[0] if place else None,
        line=place[1] if place else None,
        code=exception["type"] if exception else error.type,
    )


def _innermost_place(lines: Sequence[str], root: str) -> tuple[str, int] | None:
    places = (_place(line, root) for line in reversed(lines))
    return next((place for place in places if place is not None), None)


def _place(line: str, root: str) -> tuple[str, int] | None:
    """The line's frame, when it names a file in the project folder `root`."""
    frame = PYTHON_FILE_FRAME.search(line) or PYTHON_SHORT_FRAME.match(line)
    if frame is None:
        return None
    path = _in_project(frame["file"], root)
    return (path, int(frame["line"])) if path else None


def _in_project(path: str, root: str) -> str | None:
    """`path` relative to the project folder `root`, which relative paths already are; None for a
    file outside it."""
    if path.startswith(ABSOLUTE_PREFIX):
        folder = f"{root}{ABSOLUTE_PREFIX}"
        return path.removeprefix(folder) if path.startswith(folder) else None
    return None if path.startswith(PARENT_PREFIX) else path


def _last_exception(lines: Sequence[str]) -> re.Match[str] | None:
    exceptions = (PYTHON_EXCEPTION.match(line) for line in reversed(lines))
    return next((exception for exception in exceptions if exception is not None), None)


@dataclass(frozen=True, slots=True)
class SolutionFiles:
    """The files of a problem that is not a project, from the workspace root
    (docs/specs/cli.md#solution-file-targets)."""

    user_file: str
    package: str | None = None
    """On the JVM and in Go, the problem's package directory: every source file directly in it is
    the problem's."""

    def path_of(self, file: str) -> str | None:
        """The workspace path of a file a tool named, when it is the problem's: the user file by
        the end of its path, as a runner's trace names it by its file name (`two_sum.py`) and
        `tsc` from its own directory (`practice/two-sum.ts`), or a file of the package by its
        name. None for any other file."""
        if self.user_file == file or self.user_file.endswith(f"{PATH_SEPARATOR}{file}"):
            return self.user_file
        if self.package is not None and PATH_SEPARATOR not in file:
            return f"{self.package}{PATH_SEPARATOR}{file}"
        return None


def solution_load_diagnostic(error: UserError, files: SolutionFiles) -> Diagnostic:
    """Code of a problem that is not a project that did not load, at the innermost frame of its
    trace that lies in a file of the problem; without a place when no frame does."""
    places = (_solution_place(frame, files) for frame in reversed(error.trace.splitlines()))
    place = next((place for place in places if place is not None), None)
    return replace(
        load_diagnostic(UserError(error.type, error.message)),
        file=place[0] if place else None,
        line=place[1] if place else None,
    )


def _solution_place(frame: str, files: SolutionFiles) -> tuple[str, int] | None:
    found = TRACE_FRAME.fullmatch(frame)
    path = files.path_of(found["file"]) if found else None
    return (path, int(found["line"])) if found and path else None


def in_solution_files(diagnostic: Diagnostic, files: SolutionFiles) -> Diagnostic:
    """A tool's diagnostic with its file given from the workspace root when it is the problem's;
    any other file as the tool named it."""
    path = files.path_of(diagnostic.file) if diagnostic.file is not None else None
    return replace(diagnostic, file=path) if path else diagnostic


def distinct(diagnostics: Iterable[Diagnostic]) -> tuple[Diagnostic, ...]:
    """Each diagnostic once, where it first appears: files that import one broken module all
    fail on its line."""
    return tuple(dict.fromkeys(diagnostics))
