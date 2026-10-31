"""`go build` and `go vet` output as structured diagnostics (docs/specs/cli.md#diagnostics)."""

import pytest

from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity
from coding_study.domain.diagnostics_go import GoReport
from tests.domain.recorded_output import recorded

USER_FILE = "go/practice/two_sum/two_sum.go"


def parsed(*lines: str) -> tuple[Diagnostic, ...]:
    return GoReport().parse("\n".join(lines))


@pytest.fixture(scope="module")
def captured() -> tuple[Diagnostic, ...]:
    return GoReport().parse(recorded("go.txt"))


def test_a_captured_build_has_each_error_at_its_place(captured):
    assert [(d.line, d.column) for d in captured] == [
        (5, 2),
        (13, 6),
        (13, 18),
        (14, 14),
        (15, 11),
        (16, 6),
        (16, 17),
        (17, 9),
    ]


def test_a_diagnostic_is_read_with_its_place_and_message():
    assert parsed(f"{USER_FILE}:14:14: undefined: undefinedName") == (
        Diagnostic(
            message="undefined: undefinedName",
            source=DiagnosticSource.BUILD,
            severity=Severity.ERROR,
            file=USER_FILE,
            line=14,
            column=14,
        ),
    )


def test_go_names_no_code_for_a_problem(captured):
    assert {d.code for d in captured} == {None}


def test_the_indented_lines_below_a_diagnostic_continue_its_message(captured):
    assert captured[4].message.splitlines() == [
        "not enough arguments in call to pair",
        "\thave (number)",
        "\twant (int, int)",
    ]


def test_a_diagnostic_without_a_column_has_none():
    (diagnostic,) = parsed("go/practice/two_sum/two_sum.go:3: syntax error")
    assert (diagnostic.line, diagnostic.column) == (3, None)


def test_a_package_header_is_left_out():
    assert parsed("# command-line-arguments", f"{USER_FILE}:3:1: x") == parsed(
        f"{USER_FILE}:3:1: x"
    )


def test_a_file_of_the_directory_go_ran_in_is_named_without_dot_slash():
    diagnostics = GoReport().parse(recorded("go-build-plain.txt"))
    assert [d.file for d in diagnostics] == ["main.go", "main.go"]


def test_vets_prefix_is_not_part_of_the_message_or_the_file():
    diagnostics = GoReport().parse(recorded("go-vet.txt"))
    assert [(d.file, d.line, d.column) for d in diagnostics] == [
        ("main.go", 7, 17),
        ("main.go", 6, 14),
    ]


def test_a_vet_finding_is_read_like_a_compiler_error():
    diagnostics = GoReport().parse(recorded("go-vet.txt"))
    assert diagnostics[1].message == 'fmt.Printf format %d has arg "text" of wrong type string'


def test_a_line_that_is_not_a_diagnostic_is_left_out():
    assert parsed("", "too many errors", "go: updates to go.mod needed") == ()


def test_a_line_that_continues_nothing_is_left_out():
    assert parsed("\tstray") == ()
