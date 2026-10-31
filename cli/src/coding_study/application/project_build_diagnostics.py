"""Where a project's code did not compile (docs/specs/cli.md#diagnostics).

A project that does not build is reported by its runner as a `CompileError` with the compiler's
report in it: the suite's own load error for Java and Kotlin, whose trace holds the compiler's
lines, and the result of the package or test target that did not compile for Go and Rust, whose
message holds them. Each error of that report becomes a diagnostic at its place in the project
folder, by the same parser as for a single file. A report the language's parser finds nothing in
stays the one diagnostic of the load error it is in.
"""

from collections.abc import Sequence
from dataclasses import replace

from coding_study.application.project_runs import COMPILE_ERROR
from coding_study.application.run_tests import BUILD_REPORTS
from coding_study.domain.diagnostics import (
    Diagnostic,
    DiagnosticParser,
    distinct,
    in_project_folder,
    load_diagnostic,
)
from coding_study.domain.problem import Language
from coding_study.domain.project_test_runs import file_of_test, suite_diagnostics
from coding_study.domain.runs import Raised, UserError
from coding_study.domain.suite_runs import SuiteReport, SuiteTest


def project_diagnostics(
    report: SuiteReport, language: Language, root: str
) -> tuple[Diagnostic, ...]:
    """The diagnostics of a run of the project folder `root`: its compile errors read by the
    language's parser, then those of code that did not load (`suite_diagnostics`)."""
    parser = BUILD_REPORTS[language]
    suite = _read(report.load_error, parser, root)
    read_tests = [(test, _read_test(test, parser, root)) for test in report.tests]
    remaining = replace(
        report,
        tests=tuple(test for test, found in read_tests if not found),
        load_error=None if suite else report.load_error,
    )
    compiled = (diagnostic for _, found in read_tests for diagnostic in found)
    return distinct((*suite, *compiled, *suite_diagnostics(remaining, root)))


def load_error_diagnostics(
    error: UserError, language: Language, root: str
) -> tuple[Diagnostic, ...]:
    """The diagnostics of a project's load error, as `cstudy submit` gets it for a grading job:
    the errors of a compile error's report, else the one diagnostic of the load error. Paths are
    relative to the project folder `root`."""
    return _read(error, BUILD_REPORTS[language], root) or (load_diagnostic(error),)


def _read_test(test: SuiteTest, parser: DiagnosticParser | None, root: str) -> Sequence[Diagnostic]:
    """A target that did not compile, as a result whose id is the target and not one of its
    tests."""
    outcome = test.outcome
    if isinstance(outcome, Raised) and file_of_test(test.test_id) == test.test_id:
        return _read(outcome.error, parser, root)
    return ()


def _read(
    error: UserError | None, parser: DiagnosticParser | None, root: str
) -> tuple[Diagnostic, ...]:
    if error is None or parser is None or error.type != COMPILE_ERROR:
        return ()
    found = parser.parse(f"{error.message}\n{error.trace}")
    return tuple(in_project_folder(diagnostic, root) for diagnostic in found)
