"""The Rust runner's report of `cargo build` errors as structured diagnostics
(docs/specs/cli.md#diagnostics)."""

import pytest

from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity
from coding_study.domain.diagnostics_rustc import RustcReport
from tests.domain.recorded_output import recorded

USER_FILE = "rust/practice/two_sum.rs"


def parsed(*lines: str) -> tuple[Diagnostic, ...]:
    return RustcReport().parse("\n".join(lines))


@pytest.fixture(scope="module")
def captured() -> tuple[Diagnostic, ...]:
    return RustcReport().parse(recorded("rustc.txt"))


def test_a_captured_build_has_each_error_at_its_place(captured):
    assert [(d.line, d.column) for d in captured] == [(2, 22), (4, 28), (5, 5), (9, 47), (9, 5)]


def test_a_diagnostic_is_read_with_its_place_code_and_message():
    assert parsed(f"{USER_FILE}:2:22: error[E0308]: mismatched types") == (
        Diagnostic(
            message="mismatched types",
            source=DiagnosticSource.BUILD,
            severity=Severity.ERROR,
            file=USER_FILE,
            line=2,
            column=22,
            code="E0308",
        ),
    )


def test_the_error_codes_are_the_compilers(captured):
    assert [d.code for d in captured] == ["E0308", "E0599", "E0061", "E0277", "E0308"]


def test_the_label_and_notes_below_an_error_continue_its_message(captured):
    assert captured[2].message.splitlines() == [
        "this function takes 2 arguments but 3 arguments were supplied",
        "    note: function defined here",
        "    help: remove the extra argument",
    ]


def test_a_line_of_a_note_that_is_not_indented_still_continues_the_message(captured):
    assert "but trait `FromIterator<std::string::String>` is implemented for it" in (
        captured[3].message.splitlines()
    )


def test_an_error_without_a_code_has_none():
    (diagnostic,) = parsed(f"{USER_FILE}:2:22: error: expected one of `;` or `}}`")
    assert (diagnostic.code, diagnostic.message) == (None, "expected one of `;` or `}`")


def test_a_warning_is_a_warning():
    (diagnostic,) = parsed(f"{USER_FILE}:3:9: warning: unused variable: `unused`")
    assert (diagnostic.severity, diagnostic.code) == (Severity.WARNING, None)


def test_a_path_relative_to_a_project_folder_is_kept():
    (diagnostic,) = parsed("src/ledger.rs:7:5: error[E0425]: cannot find value `x` in this scope")
    assert diagnostic.file == "src/ledger.rs"


def test_a_line_before_the_first_diagnostic_is_left_out():
    assert parsed("Compiling bank v0.1.0", "    stray") == ()


def test_a_report_of_cargo_itself_has_no_diagnostics():
    assert parsed("error: failed to parse manifest at `Cargo.toml`") == ()
