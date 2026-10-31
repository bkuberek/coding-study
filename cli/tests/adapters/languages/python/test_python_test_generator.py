"""pytest files generated from a project level's visible cases
(docs/specs/problem-format.md#generated-test-files).

The layouts below are those `ruff format` produces; test_python_test_generator_checks.py runs ruff
on many generated files to keep the two in step.
"""

from collections.abc import Sequence
from dataclasses import replace

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Level
from coding_study.domain.project import Project
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature, Method, Param
from coding_study.domain.type_dsl import parse_value_type
from tests.project_builders import BANK, OPS, method, ops_case, project_meta, project_problem

GENERATOR = PythonTestGenerator()
SPEC_EXAMPLE = '''\
"""Level 1 examples of bank-project-python, written by `cstudy start`.

Yours to edit and extend: cstudy never rewrites this file.
"""

from bank.bank import Bank


def test_ex1() -> None:
    bank = Bank()
    assert bank.create_account(1, "ivy") is True
    assert bank.create_account(2, "leo") is True
    assert bank.create_account(3, "ivy") is False
    assert bank.deposit(4, "ivy", 800) == 800
    assert bank.deposit(5, "max", 50) == -1
'''
SPEC_EX1 = ops_case(
    "ex1",
    1,
    ("createAccount", [1, "ivy"], True),
    ("createAccount", [2, "leo"], True),
    ("createAccount", [3, "ivy"], False),
    ("deposit", [4, "ivy", 800], 800),
    ("deposit", [5, "max", 50], -1),
)
SIZE = method("size", 1, returns="int")
SIZE_CALL = ("size", [], 0)
"""A call that uses the instance, for tests about building it."""
HEADER_LINES = 8
"""The module docstring, a blank line, the import and two blank lines."""


def generated(*cases, meta=None, level: int = 1) -> str:
    return GENERATOR.generate(level_tests(project_problem(*cases, meta=meta), level))


def statement(
    found: Method,
    arguments: Sequence[JsonValue],
    expected: JsonValue,
    comparator: ComparatorSpec = OPS,
) -> str:
    """What the generated test makes of one call to `found`, after the constructor line."""
    signature = ClassSignature("Bank", (), (found,))
    meta = project_meta(signature=signature, comparator=comparator)
    text = generated(ops_case("ex1", 1, (found.name, arguments, expected)), meta=meta)
    return text.split("    bank = Bank()\n", 1)[1]


def lines_of(text: str) -> list[str]:
    return text.splitlines()


def test_level_1_matches_the_spec_example():
    assert generated(SPEC_EX1) == SPEC_EXAMPLE


def test_generation_is_byte_stable():
    assert generated(SPEC_EX1) == generated(SPEC_EX1)


def test_a_later_level_names_the_command_that_opens_it():
    case = ops_case("ex2", 2, ("transfer", [1, "a", "b", 5], -1))
    assert generated(case, level=2).startswith(
        '"""Level 2 examples of bank-project-python, written by `cstudy submit`.\n'
    )


def test_each_case_is_a_test_named_after_its_id():
    case = ops_case("big-1", 1, ("deposit", [1, "a", 5], -1))
    assert "\n\n\ndef test_big_1() -> None:\n" in generated(case)


def test_tests_follow_one_another_after_two_blank_lines():
    second = ops_case("ex2", 1, ("deposit", [1, "a", 5], -1))
    assert "== -1\n\n\ndef test_ex2() -> None:\n" in generated(SPEC_EX1, second)


def test_the_entry_module_provides_the_class():
    signature = ClassSignature("Shop", (), BANK.methods)
    meta = replace(project_meta(signature=signature), project=Project("shop.core"))
    case = ops_case("ex1", 1, ("deposit", [1, "a", 5], -1), class_name="Shop")
    assert "\nfrom shop.core import Shop\n" in generated(case, meta=meta)


def test_a_level_without_visible_cases_holds_only_its_header():
    assert generated() == (
        '"""Level 1 examples of bank-project-python, written by `cstudy start`.\n'
        "\n"
        "Yours to edit and extend: cstudy never rewrites this file.\n"
        '"""\n'
    )


def test_a_long_title_wraps_within_88_columns():
    meta = replace(project_meta(), slug="a-bank-project-with-a-name-long-enough-to-wrap-python")
    assert lines_of(generated(meta=meta))[:2] == [
        '"""Level 1 examples of a-bank-project-with-a-name-long-enough-to-wrap-python, written by',
        "`cstudy start`.",
    ]


# notes


def note_lines(note: str) -> list[str]:
    case = ops_case("ex1", 1, ("deposit", [1, "a", 5], -1), note=note)
    return lines_of(generated(case))[HEADER_LINES + 1 : -2]


def test_a_note_is_the_docstring_of_its_test_as_a_sentence():
    assert note_lines("deposits add up") == ['    """Deposits add up."""']


def test_a_note_keeps_its_own_sentence_ending():
    assert note_lines("does it add up?") == ['    """Does it add up?"""']


def test_a_long_note_wraps_within_88_columns_with_the_quotes_on_their_own_line():
    note = "booked transfers run at their due time, earliest due first, and count as money sent"
    assert note_lines(note) == [
        '    """Booked transfers run at their due time, earliest due first, and count as money',
        "    sent.",
        '    """',
    ]


def test_a_note_keeps_its_backslashes():
    assert note_lines(r"a \d matches") == ['    """A \\\\d matches."""']


def test_a_note_cannot_close_its_docstring():
    assert note_lines('say """hi"""') == ['    """Say ""\\"hi""\\"."""']


# exact


def test_a_void_call_stands_alone():
    reset = method("reset", 1, "timestamp: long")
    assert statement(reset, [1], None) == "    bank.reset(1)\n"


def test_an_absent_result_is_checked_with_is_none():
    name = method("nameOf", 1, "id: int", "string")
    assert statement(name, [1], None) == "    assert bank.name_of(1) is None\n"


def test_a_bool_inside_a_list_compares_with_equality():
    flags = method("flags", 1, "", "bool[]")
    assert statement(flags, [], [True, False]) == "    assert bank.flags() == [True, False]\n"


def test_a_float_result_is_a_float_literal():
    average = method("average", 1, "", "double")
    assert statement(average, [], 2.5) == "    assert bank.average() == 2.5\n"


def test_an_empty_list_result():
    names = method("names", 1, "", "list<string>")
    assert statement(names, [], []) == "    assert bank.names() == []\n"


def test_strings_take_double_quotes():
    name = method("nameOf", 1, "id: string", "string")
    assert statement(name, ["it's"], "ok") == '    assert bank.name_of("it\'s") == "ok"\n'


def test_a_string_with_more_double_quotes_takes_single_quotes():
    name = method("nameOf", 1, "id: string", "string")
    assert statement(name, ['say "hi"'], "ok") == '    assert bank.name_of(\'say "hi"\') == "ok"\n'


def test_strings_escape_backslashes_and_control_characters():
    name = method("nameOf", 1, "id: string", "string")
    assert statement(name, ["a\\b\n\x01"], "ok") == (
        '    assert bank.name_of("a\\\\b\\n\\x01") == "ok"\n'
    )


def test_decimal_and_date_values_are_built_from_their_text():
    due = method("dueOn", 1, "day: date", "decimal")
    assert statement(due, ["2026-01-01"], "2.50") == (
        '    assert bank.due_on(date.fromisoformat("2026-01-01")) == Decimal("2.50")\n'
    )


def test_a_whole_decimal_is_built_from_an_int_as_ruff_prefers():
    due = method("dueOn", 1, "amount: decimal", "decimal")
    assert statement(due, ["-10"], "0") == "    assert bank.due_on(Decimal(-10)) == Decimal(0)\n"


def test_a_negative_zero_decimal_keeps_its_text_and_its_sign():
    due = method("dueOn", 1, "amount: decimal", "bool")
    assert statement(due, ["-0"], True) == '    assert bank.due_on(Decimal("-0")) is True\n'


def test_decimal_and_date_values_import_their_types_in_isort_order():
    due = method("dueOn", 1, "day: date", "decimal")
    meta = project_meta(signature=ClassSignature("Bank", (), (due,)))
    text = generated(ops_case("ex1", 1, ("dueOn", ["2026-01-01"], "2.50")), meta=meta)
    assert lines_of(text)[5:9] == [
        "from datetime import date",
        "from decimal import Decimal",
        "",
        "from bank.bank import Bank",
    ]


def test_the_class_takes_the_constructor_arguments():
    signature = ClassSignature("Bank", (Param("currency", parse_value_type("string")),), (SIZE,))
    meta = project_meta(signature=signature, levels=(Level(1, "Accounts"),))
    text = generated(ops_case("ex1", 1, SIZE_CALL, constructor=["eur"]), meta=meta)
    assert '    bank = Bank("eur")\n' in text


def test_a_case_with_only_the_constructor_builds_the_class_without_naming_it():
    text = generated(ops_case("ex1", 1))
    assert text.endswith("def test_ex1() -> None:\n    Bank()\n")


def test_the_instance_is_named_after_the_class():
    signature = ClassSignature("LRUCache", (), (SIZE,))
    meta = project_meta(signature=signature)
    text = generated(ops_case("ex1", 1, SIZE_CALL, class_name="LRUCache"), meta=meta)
    assert "    lru_cache = LRUCache()\n" in text


def test_an_instance_name_that_is_a_keyword_takes_a_trailing_underscore():
    signature = ClassSignature("Lambda", (), (SIZE,))
    case = ops_case("ex1", 1, SIZE_CALL, class_name="Lambda")
    text = generated(case, meta=project_meta(signature=signature))
    assert "    lambda_ = Lambda()\n" in text


# unordered


def test_unordered_results_are_sorted_against_a_sorted_literal():
    top = method("top", 1, "n: int", "list<string>")
    unordered = ComparatorSpec(ComparatorType.OPS, per_method={"top": ComparatorType.UNORDERED})
    assert statement(top, [2], ["zoe", "abe"], unordered) == (
        '    assert sorted(bank.top(2)) == ["abe", "zoe"]\n'
    )


def test_unordered_decimals_sort_by_value():
    amounts = method("amounts", 1, "", "list<decimal>")
    unordered = ComparatorSpec(ComparatorType.OPS, per_method={"amounts": ComparatorType.UNORDERED})
    assert statement(amounts, [], ["10", "9.5"], unordered) == (
        '    assert sorted(bank.amounts()) == [Decimal("9.5"), Decimal(10)]\n'
    )


# float


FLOAT = ComparatorSpec(ComparatorType.OPS, per_method={"average": ComparatorType.FLOAT})


def test_float_results_compare_with_approx_at_the_tolerance():
    average = method("average", 1, "", "double")
    assert statement(average, [], 2.5, FLOAT) == (
        "    assert bank.average() == pytest.approx(2.5, rel=1e-06, abs=1e-06)\n"
    )


def test_float_comparisons_import_pytest_before_the_project():
    average = method("average", 1, "", "double")
    meta = project_meta(signature=ClassSignature("Bank", (), (average,)), comparator=FLOAT)
    text = generated(ops_case("ex1", 1, ("average", [], 2.5)), meta=meta)
    assert lines_of(text)[5:8] == ["import pytest", "", "from bank.bank import Bank"]


def test_a_list_of_floats_compares_with_one_approx():
    average = method("average", 1, "", "double[]")
    assert statement(average, [], [1.5, 2], FLOAT) == (
        "    assert bank.average() == pytest.approx([1.5, 2], rel=1e-06, abs=1e-06)\n"
    )


def test_nested_lists_of_floats_compare_each_inner_list_with_approx():
    average = method("average", 1, "", "double[][]")
    assert statement(average, [], [[1.5]], FLOAT) == (
        "    assert bank.average() == [pytest.approx([1.5], rel=1e-06, abs=1e-06)]\n"
    )


def test_a_float_comparison_without_numbers_stays_exact():
    average = method("average", 1, "", "bool")
    assert statement(average, [], True, FLOAT) == "    assert bank.average() is True\n"


# layouts too long for one line


SCHEDULE = method(
    "scheduleTransfer",
    1,
    "timestamp: long; sourceId: string; targetId: string; amount: long; delay: long",
    "string",
)
TOP = method("topSpenders", 1, "timestamp: long; n: int", "list<string>")
LONG_NAME = "account-with-a-very-very-long-name"


def test_a_long_comparison_with_a_plain_result_is_parenthesized():
    arguments = [1000000, "account-with-long-name", "another-long-name", 5, 1]
    assert statement(SCHEDULE, arguments, "transfer1") == (
        "    assert (\n"
        "        bank.schedule_transfer(\n"
        '            1000000, "account-with-long-name", "another-long-name", 5, 1\n'
        "        )\n"
        '        == "transfer1"\n'
        "    )\n"
    )


def test_a_comparison_that_fits_within_parentheses_stays_on_one_line():
    balance = method("balanceOfAccount", 1, "timestamp: long; accountId: string", "long")
    assert statement(balance, [1000000, f"{LONG_NAME}-xx"], -1) == (
        f'    assert (\n        bank.balance_of_account(1000000, "{LONG_NAME}-xx") == -1\n    )\n'
    )


def test_a_long_list_result_breaks_one_item_per_line():
    expected: list[JsonValue] = [
        "nia(700)",
        "oz(450)",
        "pam(0)",
        "abc(1)",
        "def(2)",
        "ghi(3)",
        "jkl(4)",
    ]
    assert statement(TOP, [10, 3], expected) == (
        "    assert bank.top_spenders(10, 3) == [\n"
        + "".join(f'        "{item}",\n' for item in expected)
        + "    ]\n"
    )


def test_a_list_of_one_long_item_takes_no_trailing_comma():
    expected: list[JsonValue] = ["single-element-that-is-really-long-and-does-not-fit-on-the-line"]
    assert statement(TOP, [1, 1], expected) == (
        "    assert bank.top_spenders(1, 1) == [\n"
        '        "single-element-that-is-really-long-and-does-not-fit-on-the-line"\n'
        "    ]\n"
    )


def test_a_long_call_breaks_first_when_the_list_still_fits_after_it():
    names = method(
        "scheduleTransfers", 1, "timestamp: long; accountId: string; other: string", "list<string>"
    )
    assert statement(names, [1000000, LONG_NAME, "x"], ["nia(700)", "oz(450)", "pam(0)"]) == (
        "    assert bank.schedule_transfers(\n"
        f'        1000000, "{LONG_NAME}", "x"\n'
        '    ) == ["nia(700)", "oz(450)", "pam(0)"]\n'
    )


def test_a_long_approx_breaks_its_own_arguments():
    average = method("average", 1, "timestamp: long; accountId: string", "double")
    assert statement(average, [10, "account-with-a-name-that-is-long"], 2.5, FLOAT) == (
        '    assert bank.average(10, "account-with-a-name-that-is-long") == pytest.approx(\n'
        "        2.5, rel=1e-06, abs=1e-06\n"
        "    )\n"
    )


def test_a_long_void_call_puts_each_argument_on_its_own_line():
    book = method(
        "book", 1, "timestamp: long; sourceId: string; targetId: string; amount: long; delay: long"
    )
    arguments = [1000000, LONG_NAME, "another-very-very-long-name", 5000000, 77]
    assert statement(book, arguments, None) == (
        "    bank.book(\n"
        "        1000000,\n"
        f'        "{LONG_NAME}",\n'
        '        "another-very-very-long-name",\n'
        "        5000000,\n"
        "        77,\n"
        "    )\n"
    )


def test_a_long_constructor_breaks_its_arguments():
    params = tuple(
        Param(name, parse_value_type(type_text))
        for name, type_text in (("a", "long"), ("b", "string"), ("c", "string"), ("d", "int"))
    )
    meta = project_meta(signature=ClassSignature("Bank", params, (SIZE,)))
    arguments = [1000000, LONG_NAME, "another-very-very-long-name", 50]
    text = generated(ops_case("ex1", 1, SIZE_CALL, constructor=arguments), meta=meta)
    assert (
        "    bank = Bank(\n"
        f'        1000000, "{LONG_NAME}", "another-very-very-long-name", 50\n'
        "    )\n"
    ) in text


def test_an_assertion_too_long_to_reach_its_first_bracket_is_parenthesized():
    long_method = method("methodWithAnExtremelyLongNameThatIsLong", 1, "n: int", "int[]")
    signature = ClassSignature("BankAccountWithExtremelyLongInstanceName", (), (long_method,))
    case = ops_case(
        "ex1",
        1,
        (long_method.name, [1], [1]),
        class_name="BankAccountWithExtremelyLongInstanceName",
    )
    text = generated(case, meta=project_meta(signature=signature))
    instance = "bank_account_with_extremely_long_instance_name"
    assert text.endswith(
        "    assert (\n"
        f"        {instance}.method_with_an_extremely_long_name_that_is_long(\n"
        "            1\n"
        "        )\n"
        "        == [1]\n"
        "    )\n"
    )


def test_a_constructor_too_long_without_arguments_to_break_is_parenthesized():
    name = "BankAccountWithAnExtremelyLongNameThatNeedsParentheses"
    case = ops_case("ex1", 1, SIZE_CALL, class_name=name)
    text = generated(case, meta=project_meta(signature=ClassSignature(name, (), (SIZE,))))
    assert (
        "    bank_account_with_an_extremely_long_name_that_needs_parentheses = (\n"
        "        BankAccountWithAnExtremelyLongNameThatNeedsParentheses()\n"
        "    )\n"
    ) in text
