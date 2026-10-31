"""Structured diagnostics from a runner's load errors (docs/specs/cli.md#diagnostics)."""

from coding_study.domain.diagnostics import (
    Diagnostic,
    DiagnosticSource,
    Severity,
    distinct,
    load_diagnostic,
    report_diagnostic,
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


ROOT = "/ws/projects/bank-project-python"
CONFTEST_SYNTAX = f"""ImportError while loading conftest '{ROOT}/tests/conftest.py'.
tests/conftest.py:5: in <module>
    from bank.bank import Bank
/opt/cs/runners/python/src/cs_runner/loading.py:40: in get_code
    return self.source_to_code(self.get_data(self.path), self.path)
E     File "{ROOT}/bank/bank.py", line 3
E       def broken(:
E                  ^
E   SyntaxError: invalid syntax"""
CONFTEST_NAME = f"""ImportError while loading conftest '{ROOT}/tests/conftest.py'.
tests/conftest.py:5: in <module>
    from bank.bank import Bank
bank/bank.py:3: in <module>
    x = undefined
E   NameError: name 'undefined' is not defined"""


def reported(text: str) -> Diagnostic:
    return report_diagnostic(UserError("UsageError", text), ROOT)


def test_a_frameworks_report_points_at_its_innermost_place_in_the_project():
    assert (reported(CONFTEST_SYNTAX).file, reported(CONFTEST_SYNTAX).line) == ("bank/bank.py", 3)


def test_a_short_frame_in_a_frameworks_report_is_a_place():
    assert (reported(CONFTEST_NAME).file, reported(CONFTEST_NAME).line) == ("bank/bank.py", 3)


def test_a_frameworks_report_names_its_last_exception():
    assert (reported(CONFTEST_SYNTAX).code, reported(CONFTEST_SYNTAX).message) == (
        "SyntaxError",
        "invalid syntax",
    )


def test_frames_outside_the_project_are_no_place():
    text = 'E     File "/opt/lib/python3.13/ast.py", line 52\nE   SyntaxError: bad'
    assert (reported(text).file, reported(text).line) == (None, None)


def test_a_relative_frame_above_the_project_is_no_place():
    assert reported("../other/bank.py:3: in <module>").file is None


def test_a_report_without_an_exception_keeps_the_error():
    text = "ERROR: usage: pytest [options]\npytest: error: unrecognized arguments: -x"
    assert (reported(text).code, reported(text).message) == ("UsageError", text)


def test_a_frameworks_report_is_an_error_from_loading():
    diagnostic = reported(CONFTEST_SYNTAX)
    assert (diagnostic.severity, diagnostic.source) == (Severity.ERROR, DiagnosticSource.LOAD)
