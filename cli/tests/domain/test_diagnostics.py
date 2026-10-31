"""Structured diagnostics from a runner's load errors (docs/specs/cli.md#diagnostics)."""

from coding_study.domain.diagnostics import (
    Diagnostic,
    DiagnosticSource,
    Severity,
    distinct,
    load_diagnostic,
)
from coding_study.domain.runs import UserError

IMPORTED = "tests/test_level_1.py:1 in <module>\nbank/bank.py:12 in Bank.deposit"
SYNTAX = UserError("SyntaxError", "invalid syntax (bank.py, line 5)", "bank/bank.py:5")


def test_a_load_error_points_at_its_innermost_frame():
    diagnostic = load_diagnostic(UserError("NameError", "name 'x' is not defined", IMPORTED))
    assert (diagnostic.file, diagnostic.line) == ("bank/bank.py", 12)


def test_a_frame_without_a_function_is_located():
    assert (load_diagnostic(SYNTAX).file, load_diagnostic(SYNTAX).line) == ("bank/bank.py", 5)


def test_a_load_error_names_no_column():
    assert load_diagnostic(SYNTAX).column is None


def test_a_load_error_keeps_the_exception_type_as_its_code():
    assert load_diagnostic(SYNTAX).code == "SyntaxError"


def test_a_load_error_keeps_its_message():
    assert load_diagnostic(SYNTAX).message == "invalid syntax (bank.py, line 5)"


def test_a_load_error_without_a_message_says_its_type():
    assert load_diagnostic(UserError("NotImplementedError", "")).message == "NotImplementedError"


def test_a_load_error_is_an_error_from_loading():
    diagnostic = load_diagnostic(SYNTAX)
    assert (diagnostic.severity, diagnostic.source) == (Severity.ERROR, DiagnosticSource.LOAD)


def test_a_load_error_without_a_trace_names_no_place():
    diagnostic = load_diagnostic(UserError("SymbolNotFound", "bank.bank has no class Bank"))
    assert (diagnostic.file, diagnostic.line) == (None, None)


def test_a_frame_in_another_format_names_no_place():
    diagnostic = load_diagnostic(UserError("KeyError", "'ivy'", 'File "bank/bank.py", line 9'))
    assert (diagnostic.file, diagnostic.line) == (None, None)


def test_a_path_with_a_colon_keeps_it():
    diagnostic = load_diagnostic(UserError("ImportError", "", "my:bank/bank.py:3 in <module>"))
    assert (diagnostic.file, diagnostic.line) == ("my:bank/bank.py", 3)


def test_repeated_diagnostics_are_kept_once_in_first_seen_order():
    first = Diagnostic("a", DiagnosticSource.LOAD, file="bank/a.py", line=1)
    second = Diagnostic("b", DiagnosticSource.LOAD)
    assert distinct([first, second, first]) == (first, second)
