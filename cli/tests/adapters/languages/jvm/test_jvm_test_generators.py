"""JUnit 5 and kotlin.test files generated from a project level's visible cases
(docs/specs/problem-format.md#generated-test-files)."""

from collections.abc import Sequence
from dataclasses import replace

import pytest

from coding_study.adapters.languages.jvm.test_generators import (
    JavaTestGenerator,
    KotlinTestGenerator,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language
from coding_study.domain.project import Project
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature, Method, Param
from coding_study.domain.type_dsl import parse_value_type
from tests.project_builders import OPS, method, ops_case, project_meta, project_problem

JAVA, KOTLIN = Language.JAVA, Language.KOTLIN
GENERATORS = {JAVA: JavaTestGenerator(), KOTLIN: KotlinTestGenerator()}
SPEC_EX1 = ops_case(
    "ex1",
    1,
    ("createAccount", [1, "ivy"], True),
    ("createAccount", [2, "leo"], True),
    ("createAccount", [3, "ivy"], False),
    ("deposit", [4, "ivy", 800], 800),
    ("deposit", [5, "max", 50], -1),
)
JAVA_SPEC_EXAMPLE = """\
// Level 1 examples of bank-project-java, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
package bank;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class Level1Test {
    @Test
    void ex1() {
        Bank bank = new Bank();
        assertTrue(bank.createAccount(1L, "ivy"));
        assertTrue(bank.createAccount(2L, "leo"));
        assertFalse(bank.createAccount(3L, "ivy"));
        assertEquals(800L, bank.deposit(4L, "ivy", 800L));
        assertEquals(-1L, bank.deposit(5L, "max", 50L));
    }
}
"""
KOTLIN_SPEC_EXAMPLE = """\
// Level 1 examples of bank-project-kotlin, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
package bank

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class Level1Test {
    @Test
    fun ex1() {
        val bank = Bank()
        assertTrue(bank.createAccount(1L, "ivy"))
        assertTrue(bank.createAccount(2L, "leo"))
        assertFalse(bank.createAccount(3L, "ivy"))
        assertEquals(800L, bank.deposit(4L, "ivy", 800L))
        assertEquals(-1L, bank.deposit(5L, "max", 50L))
    }
}
"""
CONSTRUCTION = {JAVA: "        Bank bank = new Bank();\n", KOTLIN: "        val bank = Bank()\n"}
BOTH = pytest.mark.parametrize("language", [JAVA, KOTLIN])


def generated(language: Language, *cases, meta=None, level: int = 1) -> str:
    meta = meta or project_meta(language=language)
    return GENERATORS[language].generate(level_tests(project_problem(*cases, meta=meta), level))


def statement(
    language: Language,
    found: Method,
    arguments: Sequence[JsonValue],
    expected: JsonValue,
    comparator: ComparatorSpec = OPS,
) -> str:
    """The statement a call to `found` becomes, after the constructor line."""
    signature = ClassSignature("Bank", (), (found,))
    meta = project_meta(signature=signature, comparator=comparator, language=language)
    text = generated(language, ops_case("ex1", 1, (found.name, arguments, expected)), meta=meta)
    return text.split(CONSTRUCTION[language], 1)[1].split("\n    }\n", 1)[0].strip()


def imports(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("import ")]


def compared(name: str, comparator: ComparatorType) -> ComparatorSpec:
    return ComparatorSpec(ComparatorType.OPS, per_method={name: comparator})


# whole files


def test_java_level_1_matches_the_spec_example():
    assert generated(JAVA, SPEC_EX1) == JAVA_SPEC_EXAMPLE


def test_kotlin_level_1_matches_the_spec_example():
    assert generated(KOTLIN, SPEC_EX1) == KOTLIN_SPEC_EXAMPLE


@BOTH
def test_generation_is_byte_stable(language):
    assert generated(language, SPEC_EX1) == generated(language, SPEC_EX1)


@BOTH
def test_a_later_level_names_the_command_that_opens_it(language):
    case = ops_case("ex2", 2, ("transfer", [1, "a", "b", 5], -1))
    assert generated(language, case, level=2).startswith(
        f"// Level 2 examples of bank-project-{language}, written by `cstudy submit`.\n"
    )


@BOTH
def test_a_later_level_is_its_own_test_class(language):
    case = ops_case("ex2", 2, ("transfer", [1, "a", "b", 5], -1))
    assert "\nclass Level2Test {\n" in generated(language, case, level=2)


def test_a_java_level_without_visible_cases_is_an_empty_class():
    assert generated(JAVA).endswith("package bank;\n\nclass Level1Test {}\n")


def test_a_kotlin_level_without_visible_cases_is_an_empty_class():
    assert generated(KOTLIN).endswith("package bank\n\nclass Level1Test\n")


def test_a_long_title_wraps_within_100_columns():
    meta = replace(
        project_meta(language=JAVA), slug="a-bank-project-with-a-name-long-enough-to-wrap-java"
    )
    assert generated(JAVA, meta=meta).splitlines()[:2] == [
        "// Level 1 examples of a-bank-project-with-a-name-long-enough-to-wrap-java, written by",
        "// `cstudy start`.",
    ]


@BOTH
def test_tests_are_separated_by_a_blank_line(language):
    second = ops_case("ex2", 1, ("deposit", [1, "a", 5], -1))
    text = generated(language, SPEC_EX1, second)
    assert "    }\n\n    @Test\n" in text


# names


@pytest.mark.parametrize(
    ("language", "case_id", "declared"),
    [
        (JAVA, "big-1", "void big_1()"),
        (JAVA, "1st", "void case_1st()"),
        (JAVA, "new", "void case_new()"),
        (KOTLIN, "big-1", "fun `big-1`()"),
        (KOTLIN, "1st", "fun `1st`()"),
        (KOTLIN, "object", "fun `object`()"),
        (KOTLIN, "h2", "fun h2()"),
    ],
)
def test_each_case_is_a_test_named_after_its_id(language, case_id, declared):
    case = ops_case(case_id, 1, ("deposit", [1, "a", 5], -1))
    assert f"    @Test\n    {declared} {{\n" in generated(language, case)


@pytest.mark.parametrize(
    ("class_name", "instance"),
    [("Bank", "bank"), ("LRUCache", "lruCache"), ("URL", "url"), ("Long", "long_")],
)
def test_the_instance_is_named_after_the_class_in_lower_camel_case(class_name, instance):
    signature = ClassSignature(class_name, (), (method("size", 1, returns="int"),))
    meta = project_meta(signature=signature, language=JAVA)
    case = ops_case("ex1", 1, ("size", [], 0), class_name=class_name)
    assert f"        {class_name} {instance} = new {class_name}();\n" in generated(
        JAVA, case, meta=meta
    )


@BOTH
def test_a_note_is_a_comment_above_its_test(language):
    case = ops_case("ex1", 1, ("deposit", [1, "a", 5], -1), note="deposits need an account")
    assert "    // Deposits need an account.\n    @Test\n" in generated(language, case)


def test_a_long_note_wraps_within_the_column_limit():
    note = "a deposit to an account that does not exist returns minus one " * 2
    case = ops_case("ex1", 1, ("deposit", [1, "a", 5], -1), note=note)
    comments = [line for line in generated(JAVA, case).splitlines() if line.startswith("    //")]
    assert len(comments) == 2
    assert all(len(line) <= 100 for line in comments)


# construction


def test_a_case_without_calls_builds_the_instance_alone_in_java():
    assert "    void ex1() {\n        new Bank();\n    }\n" in generated(JAVA, ops_case("ex1", 1))


def test_a_case_without_calls_builds_the_instance_alone_in_kotlin():
    assert "    fun ex1() {\n        Bank()\n    }\n" in generated(KOTLIN, ops_case("ex1", 1))


@pytest.mark.parametrize(
    ("language", "expected"),
    [(JAVA, 'Bank bank = new Bank(5, "usd");'), (KOTLIN, 'val bank = Bank(5, "usd")')],
)
def test_the_constructor_takes_the_case_arguments(language, expected):
    params = (
        Param("limit", parse_value_type("int")),
        Param("currency", parse_value_type("string")),
    )
    found = method("size", 1, returns="int")
    signature = ClassSignature("Bank", params, (found,))
    meta = project_meta(signature=signature, language=language)
    case = ops_case("ex1", 1, ("size", [], 0), constructor=[5, "usd"])
    assert f"        {expected}\n" in generated(language, case, meta=meta)


# calls and assertions


@pytest.mark.parametrize(
    ("language", "expected"), [(JAVA, 'bank.reset(1L, "a");'), (KOTLIN, 'bank.reset(1L, "a")')]
)
def test_a_void_call_stands_alone(language, expected):
    found = method("reset", 1, "timestamp: long; key: string")
    assert statement(language, found, [1, "a"], None) == expected


@pytest.mark.parametrize(
    ("language", "expected"),
    [(JAVA, 'assertNull(bank.find("a"));'), (KOTLIN, 'assertNull(bank.find("a"))')],
)
def test_an_absent_result_is_asserted_null(language, expected):
    found = method("find", 1, "key: string", "string")
    assert statement(language, found, ["a"], None) == expected


@pytest.mark.parametrize(
    ("returns", "value", "java"),
    [
        ("int", 5, "5"),
        ("long", -1, "-1L"),
        ("double", 2.5, "2.5"),
        ("double", 3, "3.0"),
        ("char", "a", "'a'"),
        ("char", "'", "'\\''"),
        ("string", 'say "hi"\\', '"say \\"hi\\"\\\\"'),
        ("string", "tab\tnew\nline", '"tab\\tnew\\nline"'),
    ],
)
def test_a_scalar_is_asserted_equal_to_its_java_literal(returns, value, java):
    found = method("get", 1, returns=returns)
    assert statement(JAVA, found, [], value) == f"assertEquals({java}, bank.get());"


def test_a_java_control_character_is_an_octal_escape():
    """Java decodes a `\\u` escape before it reads the literal."""
    found = method("get", 1, returns="string")
    assert statement(JAVA, found, [], "a\x01") == 'assertEquals("a\\001", bank.get());'


@pytest.mark.parametrize(
    ("returns", "value", "kotlin"),
    [
        ("int", -(2**31), "Int.MIN_VALUE"),
        ("long", -(2**63), "Long.MIN_VALUE"),
        ("long", 7, "7L"),
        ("string", "cost $5", '"cost \\$5"'),
        ("string", "a\x01", '"a\\u0001"'),
    ],
)
def test_a_scalar_is_asserted_equal_to_its_kotlin_literal(returns, value, kotlin):
    found = method("get", 1, returns=returns)
    assert statement(KOTLIN, found, [], value) == f"assertEquals({kotlin}, bank.get())"


@BOTH
def test_a_boolean_result_is_asserted_true_or_false(language):
    found = method("open", 1, returns="bool")
    end = ";" if language is JAVA else ""
    assert statement(language, found, [], False) == f"assertFalse(bank.open()){end}"


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (JAVA, 'assertEquals("2500.5", bank.total().stripTrailingZeros().toPlainString());'),
        (KOTLIN, 'assertEquals("2500.5", bank.total().stripTrailingZeros().toPlainString())'),
    ],
)
def test_a_decimal_result_is_compared_by_its_canonical_text(language, expected):
    assert statement(language, method("total", 1, returns="decimal"), [], "2500.5") == expected


@pytest.mark.parametrize(
    ("language", "argument"),
    [(JAVA, 'new BigDecimal("1.50")'), (KOTLIN, 'BigDecimal("1.50")')],
)
def test_a_decimal_argument_keeps_its_scale(language, argument):
    found = method("add", 1, "amount: decimal")
    assert statement(language, found, ["1.50"], None).startswith(f"bank.add({argument})")


@BOTH
def test_a_decimal_is_imported(language):
    found = method("add", 1, "amount: decimal")
    text = generated(
        language,
        ops_case("ex1", 1, ("add", ["1.50"], None)),
        meta=project_meta(signature=ClassSignature("Bank", (), (found,)), language=language),
    )
    end = ";" if language is JAVA else ""
    assert f"import java.math.BigDecimal{end}" in imports(text)


@BOTH
def test_a_date_is_parsed_from_its_iso_text(language):
    found = method("day", 1, returns="date")
    end = ";" if language is JAVA else ""
    assert statement(language, found, [], "2026-01-01") == (
        f'assertEquals(LocalDate.parse("2026-01-01"), bank.day()){end}'
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (JAVA, "assertEquals(2.5, bank.rate(), 2.5 * 1e-06);"),
        (KOTLIN, "assertEquals(2.5, bank.rate(), 2.5 * 1e-06)"),
    ],
)
def test_a_float_result_allows_the_comparators_tolerance(language, expected):
    found = method("rate", 1, returns="double")
    comparator = compared("rate", ComparatorType.FLOAT)
    assert statement(language, found, [], 2.5, comparator) == expected


def test_a_float_tolerance_is_at_least_the_absolute_one():
    found = method("rate", 1, returns="double")
    comparator = compared("rate", ComparatorType.FLOAT)
    assert statement(JAVA, found, [], 0.25, comparator) == "assertEquals(0.25, bank.rate(), 1e-06);"


# arrays and lists


@pytest.mark.parametrize(
    ("language", "returns", "expected"),
    [
        (JAVA, "int[]", "assertArrayEquals(new int[] {1, 2}, bank.ids());"),
        (JAVA, "string[]", 'assertArrayEquals(new String[] {"a"}, bank.ids());'),
        (KOTLIN, "int[]", "assertContentEquals(intArrayOf(1, 2), bank.ids())"),
        (KOTLIN, "long[]", "assertContentEquals(longArrayOf(1L, 2L), bank.ids())"),
        (KOTLIN, "string[]", 'assertContentEquals(arrayOf("a"), bank.ids())'),
    ],
)
def test_an_array_result_is_compared_element_by_element(language, returns, expected):
    values: list[JsonValue] = ["a"] if returns == "string[]" else [1, 2]
    assert statement(language, method("ids", 1, returns=returns), [], values) == expected


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (JAVA, "bank.load(new int[][] {{1, 2}, {3}});"),
        (KOTLIN, "bank.load(arrayOf(intArrayOf(1, 2), intArrayOf(3)))"),
    ],
)
def test_a_nested_array_argument(language, expected):
    found = method("load", 1, "grid: int[][]")
    assert statement(language, found, [[[1, 2], [3]]], None) == expected


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (JAVA, 'assertEquals(List.of("ann", "bo"), bank.names());'),
        (KOTLIN, 'assertEquals(listOf("ann", "bo"), bank.names())'),
    ],
)
def test_a_list_result_is_compared_to_a_list(language, expected):
    found = method("names", 1, returns="list<string>")
    assert statement(language, found, [], ["ann", "bo"]) == expected


def test_a_java_list_holding_null_is_built_with_arrays_as_list():
    found = method("names", 1, returns="list<string>")
    assert statement(JAVA, found, [], ["ann", None]) == (
        'assertEquals(Arrays.asList("ann", null), bank.names());'
    )


def test_a_java_list_of_longs_spells_every_long():
    found = method("ids", 1, returns="list<long>")
    assert statement(JAVA, found, [], [1, 2]) == "assertEquals(List.of(1L, 2L), bank.ids());"


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (JAVA, 'assertEquals(List.of("Zed", "ann"), bank.names().stream().sorted().toList());'),
        (KOTLIN, 'assertEquals(listOf("Zed", "ann"), bank.names().sorted())'),
    ],
)
def test_an_unordered_list_is_sorted_on_both_sides(language, expected):
    found = method("names", 1, returns="list<string>")
    comparator = compared("names", ComparatorType.UNORDERED)
    assert statement(language, found, [], ["ann", "Zed"], comparator) == expected


@pytest.mark.parametrize(
    ("language", "returns", "expected"),
    [
        (
            JAVA,
            "int[]",
            "assertArrayEquals(new int[] {1, 3}, Arrays.stream(bank.ids()).sorted().toArray());",
        ),
        (
            JAVA,
            "string[]",
            'assertArrayEquals(new String[] {"a", "b"}, '
            "Arrays.stream(bank.ids()).sorted().toArray(String[]::new));",
        ),
        (KOTLIN, "int[]", "assertContentEquals(intArrayOf(1, 3), bank.ids().sortedArray())"),
    ],
)
def test_an_unordered_array_is_sorted_on_both_sides(language, returns, expected):
    values: list[JsonValue] = ["b", "a"] if returns == "string[]" else [3, 1]
    comparator = compared("ids", ComparatorType.UNORDERED)
    text = statement(language, method("ids", 1, returns=returns), [], values, comparator)
    assert " ".join(text.split()).replace("( ", "(") == expected


def test_unordered_strings_sort_as_java_compares_them():
    """By UTF-16 code units: a character above U+FFFF sorts before U+FFE8."""
    found = method("names", 1, returns="list<string>")
    comparator = compared("names", ComparatorType.UNORDERED)
    high, astral = "\uffe8", "\U0001f600"
    text = statement(JAVA, found, [], [high, astral], comparator)
    assert text.startswith(f'assertEquals(List.of("{astral}", "{high}"),')


# imports


def test_java_imports_static_assertions_then_classes():
    found = method("names", 1, returns="list<date>")
    signature = ClassSignature("Bank", (), (found,))
    meta = replace(
        project_meta(signature=signature, language=JAVA),
        project=Project("com.bank.Bank", "src/test/java/com/bank/levels"),
    )
    text = generated(JAVA, ops_case("ex1", 1, ("names", [], ["2026-01-01"])), meta=meta)
    assert imports(text) == [
        "import static org.junit.jupiter.api.Assertions.assertEquals;",
        "import com.bank.Bank;",
        "import java.time.LocalDate;",
        "import java.util.List;",
        "import org.junit.jupiter.api.Test;",
    ]


def test_kotlin_imports_put_java_and_kotlin_last():
    found = method("day", 1, returns="date")
    signature = ClassSignature("Bank", (), (found,))
    meta = replace(
        project_meta(signature=signature, language=KOTLIN),
        project=Project("com.bank.Bank", "src/test/kotlin/levels"),
    )
    text = generated(KOTLIN, ops_case("ex1", 1, ("day", [], "2026-01-01")), meta=meta)
    assert imports(text) == [
        "import com.bank.Bank",
        "import java.time.LocalDate",
        "import kotlin.test.Test",
        "import kotlin.test.assertEquals",
    ]


@BOTH
def test_the_entry_in_the_tests_package_is_not_imported(language):
    assert not [line for line in imports(generated(language, SPEC_EX1)) if "Bank" in line]


def test_java_imports_are_a_static_block_and_a_class_block():
    text = generated(JAVA, SPEC_EX1)
    assert "assertTrue;\n\nimport org.junit.jupiter.api.Test;\n\nclass" in text


# long statements


def long_name(length: int) -> str:
    return "a" * length


def test_a_long_java_statement_puts_its_arguments_on_one_continuation_line():
    found = method("deposit", 1, "timestamp: long; accountId: string; amount: long", "long")
    text = statement(JAVA, found, [1, long_name(50), 5], -1)
    assert text.splitlines() == [
        "assertEquals(",
        f'                -1L, bank.deposit(1L, "{long_name(50)}", 5L));',
    ]


def test_a_longer_java_statement_puts_one_argument_per_line():
    found = method("deposit", 1, "timestamp: long; accountId: string; amount: long", "long")
    text = statement(JAVA, found, [1, long_name(70), 5], -1)
    assert text.splitlines() == [
        "assertEquals(",
        "                -1L,",
        "                bank.deposit(",
        "                        1L,",
        f'                        "{long_name(70)}",',
        "                        5L));",
    ]


def test_a_long_kotlin_statement_puts_one_argument_per_line_with_a_trailing_comma():
    found = method("deposit", 1, "timestamp: long; accountId: string; amount: long", "long")
    text = statement(KOTLIN, found, [1, long_name(100), 5], -1)
    assert text.splitlines() == [
        "assertEquals(",
        "            -1L,",
        f'            bank.deposit(1L, "{long_name(100)}", 5L),',
        "        )",
    ]


@BOTH
def test_every_line_fits_the_column_limit_when_it_can(language):
    found = method("names", 1, returns="list<string>")
    names: list[JsonValue] = [long_name(30) for _ in range(8)]
    limit = 100 if language is JAVA else 140
    text = generated(
        language,
        ops_case("ex1", 1, ("names", [], names)),
        meta=project_meta(signature=ClassSignature("Bank", (), (found,)), language=language),
    )
    assert max(len(line) for line in text.splitlines()) <= limit
