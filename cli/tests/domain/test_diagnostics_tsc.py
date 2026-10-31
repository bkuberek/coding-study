"""`tsc --pretty false` output as structured diagnostics (docs/specs/cli.md#diagnostics)."""

import pytest

from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity
from coding_study.domain.diagnostics_tsc import TscReport

FOLDER = "projects/bank-project-typescript"
TYPE_ERROR = (
    f"{FOLDER}/src/bank.ts(3,5): error TS2322: Type 'number' is not assignable to type 'boolean'."
)


def parsed(*lines: str) -> tuple[Diagnostic, ...]:
    return TscReport(FOLDER).parse("\n".join(lines))


def test_a_diagnostic_is_read_with_its_place_code_and_message():
    assert parsed(TYPE_ERROR) == (
        Diagnostic(
            message="Type 'number' is not assignable to type 'boolean'.",
            source=DiagnosticSource.TYPECHECK,
            severity=Severity.ERROR,
            file="src/bank.ts",
            line=3,
            column=5,
            code="TS2322",
        ),
    )


def test_diagnostics_keep_the_order_tsc_reported_them_in():
    second = f"{FOLDER}/src/ledger.ts(10,1): error TS2304: Cannot find name 'x'."
    assert [diagnostic.file for diagnostic in parsed(TYPE_ERROR, second)] == [
        "src/bank.ts",
        "src/ledger.ts",
    ]


def test_an_indented_line_continues_the_message_before_it():
    (diagnostic,) = parsed(TYPE_ERROR, "  Type 'number' is not 'boolean'.")
    assert diagnostic.message.splitlines() == [
        "Type 'number' is not assignable to type 'boolean'.",
        "  Type 'number' is not 'boolean'.",
    ]


@pytest.mark.parametrize(
    ("category", "severity"),
    [("error", Severity.ERROR), ("warning", Severity.WARNING), ("message", Severity.INFO)],
)
def test_each_category_has_its_severity(category, severity):
    (diagnostic,) = parsed(f"{FOLDER}/src/bank.ts(1,1): {category} TS6133: 'x' is unused.")
    assert diagnostic.severity is severity


def test_a_file_outside_the_folder_is_named_from_it():
    (diagnostic,) = parsed("typescript/support.ts(2,3): error TS2307: Cannot find module.")
    assert diagnostic.file == "../../typescript/support.ts"


def test_a_diagnostic_without_a_file_has_no_place():
    (diagnostic,) = parsed("error TS5083: Cannot read file 'tsconfig.json'.")
    assert (diagnostic.file, diagnostic.line, diagnostic.code) == (None, None, "TS5083")


def test_lines_that_are_not_diagnostics_are_left_out():
    assert parsed("", "Found 1 error.") == ()
