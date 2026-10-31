"""`javac` output as structured diagnostics (docs/specs/cli.md#diagnostics)."""

import pytest

from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity
from coding_study.domain.diagnostics_javac import JavacReport
from tests.domain.recorded_output import recorded

SOLUTION = "/ws/jvm/java/src/main/java/practice/two_sum/Solution.java"


def parsed(*lines: str) -> tuple[Diagnostic, ...]:
    return JavacReport().parse("\n".join(lines))


@pytest.fixture(scope="module")
def captured() -> tuple[Diagnostic, ...]:
    return JavacReport().parse(recorded("javac.txt"))


def test_a_captured_build_has_each_error_and_warning_and_note(captured):
    assert [(d.severity, d.line) for d in captured] == [
        (Severity.ERROR, 7),
        (Severity.ERROR, 9),
        (Severity.ERROR, 10),
        (Severity.ERROR, 11),
        (Severity.WARNING, 12),
        (Severity.ERROR, 17),
        (Severity.INFO, None),
    ]


def test_the_caret_line_gives_the_column(captured):
    assert [d.column for d in captured[:6]] == [21, 19, 22, 9, 25, 16]


def test_a_diagnostic_is_read_with_its_place_and_message():
    assert parsed(
        f"{SOLUTION}:7: error: incompatible types: String cannot be converted to int",
        '        int count = "five";',
        "                    ^",
    ) == (
        Diagnostic(
            message="incompatible types: String cannot be converted to int",
            source=DiagnosticSource.BUILD,
            severity=Severity.ERROR,
            file=SOLUTION,
            line=7,
            column=21,
        ),
    )


def test_the_source_line_and_caret_are_not_part_of_the_message(captured):
    assert "five" not in captured[0].message


def test_the_lines_below_the_caret_continue_the_message(captured):
    assert captured[1].message.splitlines() == [
        "cannot find symbol",
        "  symbol:   variable undefinedName",
        "  location: class Solution",
    ]


def test_a_lint_category_in_brackets_is_the_code(captured):
    warning = captured[4]
    assert (warning.code, warning.message) == (
        "removal",
        "Integer(int) in Integer has been deprecated and marked for removal",
    )


def test_an_error_has_no_code(captured):
    assert captured[0].code is None


def test_a_note_names_its_file_and_no_line(captured):
    note = captured[6]
    assert (note.file, note.message) == (SOLUTION, "uses unchecked or unsafe operations.")


def test_a_note_without_a_file_is_a_message_alone():
    (note,) = parsed("Note: Recompile with -Xlint:unchecked for details.")
    assert (note.severity, note.file, note.message) == (
        Severity.INFO,
        None,
        "Recompile with -Xlint:unchecked for details.",
    )


def test_a_source_line_at_the_left_margin_is_not_a_continuation():
    (diagnostic,) = parsed(
        f"{SOLUTION}:3: error: class, interface, enum, or record expected",
        "int stray;",
        "^",
    )
    assert (diagnostic.column, diagnostic.message) == (
        1,
        "class, interface, enum, or record expected",
    )


def test_a_tab_in_the_source_line_counts_as_one_column():
    (diagnostic,) = parsed(
        f"{SOLUTION}:4: error: ';' expected",
        "\treturn 1",
        "\t        ^",
    )
    assert diagnostic.column == 10


def test_a_report_without_a_caret_keeps_its_indented_lines_in_the_message():
    (diagnostic,) = parsed(f"{SOLUTION}:4: error: x", "  detail")
    assert (diagnostic.column, diagnostic.message) == (None, "x\n  detail")


def test_an_error_without_a_file_has_no_place():
    (diagnostic,) = parsed("error: invalid flag: -bogus")
    assert (diagnostic.file, diagnostic.line, diagnostic.message) == (
        None,
        None,
        "invalid flag: -bogus",
    )


def test_a_relative_path_is_kept_as_it_is():
    (diagnostic,) = parsed("src/main/java/bank/Bank.java:3: error: ';' expected")
    assert diagnostic.file == "src/main/java/bank/Bank.java"


def test_gradles_count_of_errors_is_left_out():
    assert parsed(f"{SOLUTION}:3: error: x", "        y;", "        ^", "1 error") == parsed(
        f"{SOLUTION}:3: error: x", "        y;", "        ^"
    )


def test_output_without_diagnostics_gives_none():
    assert parsed("", "BUILD FAILED in 1s") == ()
