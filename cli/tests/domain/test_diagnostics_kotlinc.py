"""`kotlinc` output, as Gradle prints it, as structured diagnostics
(docs/specs/cli.md#diagnostics)."""

import pytest

from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity
from coding_study.domain.diagnostics_kotlinc import KotlincReport
from tests.domain.recorded_output import recorded

SOLUTION = "/ws/jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt"


def parsed(*lines: str) -> tuple[Diagnostic, ...]:
    return KotlincReport().parse("\n".join(lines))


@pytest.fixture(scope="module")
def captured() -> tuple[Diagnostic, ...]:
    return KotlincReport().parse(recorded("kotlinc.txt"))


def test_a_captured_build_has_each_error_at_its_place(captured):
    assert [(d.line, d.column) for d in captured] == [(8, 24), (9, 17), (10, 17), (15, 16)]


def test_a_diagnostic_is_read_with_its_place_and_message():
    assert parsed(f"e: file://{SOLUTION}:8:24 Initializer type mismatch: expected 'Int'.") == (
        Diagnostic(
            message="Initializer type mismatch: expected 'Int'.",
            source=DiagnosticSource.BUILD,
            severity=Severity.ERROR,
            file=SOLUTION,
            line=8,
            column=24,
        ),
    )


def test_the_file_url_is_a_path(captured):
    assert {d.file for d in captured} == {SOLUTION}


def test_a_captured_warning_is_a_warning():
    (warning,) = KotlincReport().parse(recorded("kotlinc-warnings.txt"))
    assert (warning.severity, warning.line, warning.message) == (
        Severity.WARNING,
        9,
        "'fun old(): Int' is deprecated. old.",
    )


def test_an_info_line_is_info():
    (info,) = parsed(f"i: file://{SOLUTION}:2:1 Something to know.")
    assert info.severity is Severity.INFO


def test_kotlinc_has_no_code_for_a_problem(captured):
    assert {d.code for d in captured} == {None}


def test_a_path_relative_to_a_project_folder_is_kept():
    (diagnostic,) = parsed("e: src/main/kotlin/bank/Bank.kt:1:31 Return type mismatch.")
    assert (diagnostic.file, diagnostic.line, diagnostic.column) == (
        "src/main/kotlin/bank/Bank.kt",
        1,
        31,
    )


def test_an_indented_line_continues_the_message_before_it():
    (diagnostic,) = parsed(f"e: file://{SOLUTION}:3:5 Cannot infer type.", "  Specify it.")
    assert diagnostic.message == "Cannot infer type.\n  Specify it."


def test_an_unindented_line_after_a_diagnostic_is_not_part_of_it():
    (diagnostic,) = parsed(f"e: file://{SOLUTION}:3:5 Cannot infer type.", "BUILD FAILED")
    assert diagnostic.message == "Cannot infer type."


def test_an_error_without_a_place_has_none():
    (diagnostic,) = parsed("e: Could not load module <main>")
    assert (diagnostic.file, diagnostic.line, diagnostic.message) == (
        None,
        None,
        "Could not load module <main>",
    )


def test_diagnostics_keep_the_order_kotlinc_reported_them_in():
    first = f"e: file://{SOLUTION}:9:1 B."
    second = f"w: file://{SOLUTION}:2:1 A."
    assert [d.line for d in parsed(first, second)] == [9, 2]


def test_a_line_that_is_not_a_diagnostic_is_left_out():
    assert parsed("", "> Task :kotlin:compileKotlin FAILED", "v: loaded plugin") == ()
