"""Go `testing` files generated from a project level's visible cases
(docs/specs/problem-format.md#go-test-files).

test_go_test_generator_checks.py runs gofmt, `go vet` and `go test` on generated files to keep
these layouts in step with the toolchain.
"""

from collections.abc import Sequence
from dataclasses import replace

import pytest

from coding_study.adapters.languages.go.test_generator import GoTestGenerator
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language
from coding_study.domain.project import Project
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature, Method
from tests.project_builders import OPS, method, ops_case, project_meta, project_problem

GENERATOR = GoTestGenerator()
SPEC_EXAMPLE = """\
// Level 1 examples of bank-project-go, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.

package tests_test

import (
\t"testing"

\tbank "bank-project-go"
)

func TestEx1(t *testing.T) {
\tb := bank.NewBank()
\tif got := b.CreateAccount(1, "ivy"); !got {
\t\tt.Errorf(`b.CreateAccount(1, "ivy") = %v, want true`, got)
\t}
\tif got := b.CreateAccount(3, "ivy"); got {
\t\tt.Errorf(`b.CreateAccount(3, "ivy") = %v, want false`, got)
\t}
\tif got := b.Deposit(4, "ivy", 800); got != 800 {
\t\tt.Errorf(`b.Deposit(4, "ivy", 800) = %v, want 800`, got)
\t}
}
"""
SPEC_EX1 = ops_case(
    "ex1",
    1,
    ("createAccount", [1, "ivy"], True),
    ("createAccount", [3, "ivy"], False),
    ("deposit", [4, "ivy", 800], 800),
)
DEPOSIT_CALL = ("deposit", [1, "a", 5], -1)
GO_META = project_meta(language=Language.GO)
FLOAT = ComparatorSpec(ComparatorType.OPS, per_method={"report": ComparatorType.FLOAT})
UNORDERED = ComparatorSpec(ComparatorType.OPS, per_method={"report": ComparatorType.UNORDERED})


def generated(*cases, meta=GO_META, level: int = 1) -> str:
    return GENERATOR.generate(level_tests(project_problem(*cases, meta=meta), level))


def go_meta(signature: ClassSignature, comparator: ComparatorSpec = OPS):
    return project_meta(signature=signature, comparator=comparator, language=Language.GO)


def statement(
    found: Method,
    arguments: Sequence[JsonValue],
    expected: JsonValue,
    comparator: ComparatorSpec = OPS,
) -> str:
    """What the generated test makes of one call to `found`, after the constructor line."""
    meta = go_meta(ClassSignature("Bank", (), (found,)), comparator)
    text = generated(ops_case("ex1", 1, (found.name, arguments, expected)), meta=meta)
    return text.split("\tb := bank.NewBank()\n", 1)[1].removesuffix("}\n")


def imports(text: str) -> str:
    return text.split("import (\n", 1)[1].split("\n)\n", 1)[0]


def report(returns: str, expected: JsonValue, comparator: ComparatorSpec = OPS) -> str:
    return statement(method("report", 1, returns=returns), [], expected, comparator)


def test_level_1_matches_the_spec_example():
    assert generated(SPEC_EX1) == SPEC_EXAMPLE


def test_generation_is_byte_stable():
    assert generated(SPEC_EX1) == generated(SPEC_EX1)


def test_a_later_level_names_the_command_that_opens_it():
    case = ops_case("ex2", 2, ("transfer", [1, "a", "b", 5], -1))
    assert generated(case, level=2).startswith(
        "// Level 2 examples of bank-project-go, written by `cstudy submit`.\n"
    )


def test_each_case_is_a_test_named_after_its_id():
    assert "\nfunc TestBig_1(t *testing.T) {\n" in generated(ops_case("big-1", 1, DEPOSIT_CALL))


def test_tests_follow_one_another_after_a_blank_line():
    second = ops_case("ex2", 1, DEPOSIT_CALL)
    assert "\n}\n\nfunc TestEx2(t *testing.T) {\n" in generated(SPEC_EX1, second)


def test_a_level_without_visible_cases_holds_its_header_and_package():
    assert generated() == (
        "// Level 1 examples of bank-project-go, written by `cstudy start`.\n"
        "// Yours to edit and extend: cstudy never rewrites this file.\n"
        "\n"
        "package tests_test\n"
    )


def test_a_case_note_is_a_comment_above_its_test():
    case = ops_case("ex1", 1, DEPOSIT_CALL, note="max has no account")
    assert "\n// max has no account\nfunc TestEx1(" in generated(case)


def test_the_package_is_named_after_the_tests_directory():
    meta = replace(GO_META, project=Project("bank.go", "checks/levels"))
    assert "\npackage levels_test\n" in generated(SPEC_EX1, meta=meta)


def test_an_entry_in_a_directory_is_imported_by_the_directory_path():
    meta = replace(GO_META, project=Project("ledger/bank.go"))
    assert '\tledger "bank-project-go/ledger"' in imports(generated(SPEC_EX1, meta=meta))


def test_a_case_without_calls_builds_the_instance_alone():
    assert "\tbank.NewBank()\n}" in generated(ops_case("ex1", 1))


def test_constructor_arguments_are_go_literals():
    signature = ClassSignature("Bank", (method("x", 1, "fee: double; name: string").params), ())
    meta = go_meta(signature)
    case = ops_case("ex1", 1, constructor=[0.5, "main"])
    assert '\tbank.NewBank(0.5, "main")\n' in generated(case, meta=meta)


def test_a_void_call_stands_alone():
    close = method("close", 1, "timestamp: long; accountId: string")
    assert statement(close, [5, "ivy"], None) == '\tb.Close(5, "ivy")\n'


def test_a_list_is_compared_with_slices_equal():
    assert report("list<string>", ["a", "b"]) == (
        '\tif got := b.Report(); !slices.Equal(got, []string{"a", "b"}) {\n'
        '\t\tt.Errorf(`b.Report() = %v, want []string{"a", "b"}`, got)\n'
        "\t}\n"
    )


def test_a_list_imports_slices():
    meta = go_meta(ClassSignature("Bank", (), (method("report", 1, returns="int[]"),)))
    text = generated(ops_case("ex1", 1, ("report", [], [1])), meta=meta)
    assert imports(text) == '\t"slices"\n\t"testing"\n\n\tbank "bank-project-go"'


def test_nested_lists_are_compared_item_by_item():
    assert "!slices.EqualFunc(got, [][]int{{1, 2}, {}}, slices.Equal)" in report(
        "int[][]", [[1, 2], []]
    )


def test_a_decimal_is_compared_by_value():
    assert '!got.Equal(decimal.RequireFromString("2.5"))' in report("decimal", "2.5")


def test_a_list_of_decimals_is_compared_by_value():
    assert (
        '!slices.EqualFunc(got, []decimal.Decimal{decimal.RequireFromString("1")}, '
        "decimal.Decimal.Equal)"
    ) in report("list<decimal>", ["1"])


def test_a_decimal_imports_the_vendored_module_after_the_entry():
    meta = go_meta(ClassSignature("Bank", (), (method("report", 1, returns="decimal"),)))
    text = generated(ops_case("ex1", 1, ("report", [], "1")), meta=meta)
    assert imports(text) == (
        '\t"testing"\n\n\tbank "bank-project-go"\n\t"github.com/shopspring/decimal"'
    )


def test_a_date_is_a_utc_midnight():
    assert "got != time.Date(2026, time.March, 9, 0, 0, 0, 0, time.UTC)" in report(
        "date", "2026-03-09"
    )


def test_a_float_comparison_allows_the_tolerance():
    assert report("double", 2.5, FLOAT) == (
        "\tif got := b.Report(); !closeTo(got, 2.5) {\n"
        "\t\tt.Errorf(`b.Report() = %v, want 2.5 within 1e-06`, got)\n"
        "\t}\n"
    )


def test_a_float_comparison_defines_close_to_once():
    meta = go_meta(ClassSignature("Bank", (), (method("report", 1, returns="double"),)), FLOAT)
    case = ops_case("ex1", 1, ("report", [], 1.5), ("report", [], 2))
    assert generated(case, meta=meta).count("func closeTo(") == 1


def test_close_to_holds_within_the_tolerance_of_the_expected_value():
    meta = go_meta(ClassSignature("Bank", (), (method("report", 1, returns="double"),)), FLOAT)
    text = generated(ops_case("ex1", 1, ("report", [], 1.5)), meta=meta)
    assert (
        "func closeTo(got, want float64) bool {\n"
        "\treturn math.Abs(got-want) <= 1e-06*math.Max(1, math.Abs(want))\n"
        "}\n"
    ) in text


def test_a_list_of_floats_is_compared_item_by_item_within_the_tolerance():
    assert "!slices.EqualFunc(got, []float64{1, 2.5}, closeTo)" in report(
        "double[]", [1, 2.5], FLOAT
    )


def test_a_float_comparison_of_strings_is_exact():
    assert "got != " in report("string", "a", FLOAT)


def test_an_unordered_list_is_sorted_first():
    assert report("list<string>", ["b", "a"], UNORDERED) == (
        "\tif got := slices.Sorted(slices.Values(b.Report())); "
        '!slices.Equal(got, []string{"a", "b"}) {\n'
        '\t\tt.Errorf(`b.Report() sorted = %v, want []string{"a", "b"}`, got)\n'
        "\t}\n"
    )


def test_unordered_decimals_sort_by_value():
    found = report("list<decimal>", ["10", "9.5"], UNORDERED)
    assert "slices.SortedFunc(slices.Values(b.Report()), decimal.Decimal.Cmp)" in found
    assert '{decimal.RequireFromString("9.5"), decimal.RequireFromString("10")}' in found


def test_unordered_lists_of_lists_sort_lexicographically():
    found = report("list<list<int>>", [[2], [1, 3], [1]], UNORDERED)
    assert "slices.SortedFunc(slices.Values(b.Report()), slices.Compare)" in found
    assert "[][]int{{1}, {1, 3}, {2}}" in found


def test_unordered_dates_sort_by_time():
    found = report("list<date>", ["2026-01-02", "2026-01-01"], UNORDERED)
    assert "slices.SortedFunc(slices.Values(b.Report()), time.Time.Compare)" in found


def test_an_unordered_list_of_booleans_cannot_be_generated():
    with pytest.raises(ValueError, match="a generated Go test cannot sort a list of bool"):
        report("list<bool>", [True, False], UNORDERED)


@pytest.mark.parametrize(
    ("text", "literal"),
    [
        ("a\tb", '"a\\tb"'),
        ('say "hi"', '"say \\"hi\\""'),
        ("back\\slash", '"back\\\\slash"'),
        ("é", '"é"'),
        ("\x00", '"\\x00"'),
    ],
)
def test_strings_are_go_string_literals(text, literal):
    deposit = method("deposit", 1, "accountId: string")
    assert f"b.Deposit({literal})" in statement(deposit, [text], None)


@pytest.mark.parametrize(("text", "literal"), [("a", "'a'"), ("'", "'\\''"), ("\n", "'\\n'")])
def test_characters_are_rune_literals(text, literal):
    mark = method("mark", 1, "symbol: char")
    assert f"b.Mark({literal})" in statement(mark, [text], None)


def test_a_message_with_a_backquote_is_an_interpreted_string():
    found = report("string", "a`b")
    assert 't.Errorf("b.Report() = %v, want \\"a`b\\"", got)' in found


def test_a_percent_sign_in_a_message_is_doubled():
    found = report("string", "50%")
    assert 't.Errorf(`b.Report() = %v, want "50%%"`, got)' in found


def test_the_instance_avoids_the_testing_parameter():
    meta = go_meta(ClassSignature("Tracker", (), (method("size", 1, returns="int"),)))
    case = ops_case("ex1", 1, ("size", [], 0), class_name="Tracker")
    assert "\ttracker := bank.NewTracker()\n" in generated(case, meta=meta)


def test_the_instance_avoids_the_package_name():
    meta = replace(GO_META, project=Project("b.go"))
    assert "\tbank := b.NewBank()\n" in generated(SPEC_EX1, meta=meta)
