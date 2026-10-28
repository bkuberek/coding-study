from dataclasses import replace

import pytest

from coding_study.adapters.languages.jvm import (
    create_java_stub_generator,
    create_kotlin_stub_generator,
)
from coding_study.adapters.languages.jvm.jvm_types import java_type, kotlin_type
from coding_study.domain.problem import Language
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType, parse_value_type
from tests.stub_contract import STUB_CASES, StubCase, check_stub, stub_cases

JAVA = create_java_stub_generator()
KOTLIN = create_kotlin_stub_generator()
CASES = {case.name: case for case in STUB_CASES}
JAVA_LINE_LIMIT = 100
KOTLIN_LINE_LIMIT = 140

# docs/specs/problem-format.md, worked examples; every stub adds a header line and a blank line.
TWO_SUM_JAVA = """package practice.two_sum;

import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
"""
TWO_SUM_KOTLIN = """package practice.two_sum

class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        TODO("Not implemented")
    }
}
"""
LRU_CACHE_JAVA = """package practice.lru_cache;

import java.util.*;

public class LRUCache {
    public LRUCache(int capacity) {
    }

    public int get(int key) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public void put(int key, int value) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
"""
LRU_CACHE_KOTLIN = """package practice.lru_cache

class LRUCache(capacity: Int) {
    fun get(key: Int): Int {
        TODO("Not implemented")
    }

    fun put(key: Int, value: Int) {
        TODO("Not implemented")
    }
}
"""
TWO_SUM_HEADER = "// Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum\n\n"

# docs/specs/problem-format.md#type-mapping: DSL, Java, Kotlin.
MAPPING_TABLE = (
    ("int", "int", "Int"),
    ("long", "long", "Long"),
    ("double", "double", "Double"),
    ("bool", "boolean", "Boolean"),
    ("string", "String", "String"),
    ("char", "char", "Char"),
    ("int[]", "int[]", "IntArray"),
    ("long[]", "long[]", "LongArray"),
    ("double[]", "double[]", "DoubleArray"),
    ("bool[]", "boolean[]", "BooleanArray"),
    ("char[]", "char[]", "CharArray"),
    ("string[]", "String[]", "Array<String>"),
    ("decimal", "BigDecimal", "BigDecimal"),
    ("date", "LocalDate", "LocalDate"),
    ("decimal[]", "BigDecimal[]", "Array<BigDecimal>"),
    ("date[]", "LocalDate[]", "Array<LocalDate>"),
    ("decimal[][]", "BigDecimal[][]", "Array<Array<BigDecimal>>"),
    ("date[][]", "LocalDate[][]", "Array<Array<LocalDate>>"),
    ("list<decimal>", "List<BigDecimal>", "List<BigDecimal>"),
    ("list<date>", "List<LocalDate>", "List<LocalDate>"),
    ("int[][]", "int[][]", "Array<IntArray>"),
    ("long[][]", "long[][]", "Array<LongArray>"),
    ("double[][]", "double[][]", "Array<DoubleArray>"),
    ("bool[][]", "boolean[][]", "Array<BooleanArray>"),
    ("char[][]", "char[][]", "Array<CharArray>"),
    ("string[][]", "String[][]", "Array<Array<String>>"),
    ("list<int>", "List<Integer>", "List<Int>"),
    ("list<long>", "List<Long>", "List<Long>"),
    ("list<double>", "List<Double>", "List<Double>"),
    ("list<bool>", "List<Boolean>", "List<Boolean>"),
    ("list<char>", "List<Character>", "List<Char>"),
    ("list<string>", "List<String>", "List<String>"),
    ("list<int[]>", "List<int[]>", "List<IntArray>"),
    ("list<list<int>>", "List<List<Integer>>", "List<List<Int>>"),
    ("list<list<string>>", "List<List<String>>", "List<List<String>>"),
    ("ListNode", "ListNode", "ListNode?"),
    ("TreeNode", "TreeNode", "TreeNode?"),
    ("GraphNode", "GraphNode", "GraphNode?"),
    ("ListNode[]", "ListNode[]", "Array<ListNode?>"),
    ("list<TreeNode>", "List<TreeNode>", "List<TreeNode?>"),
)


def generated(language: Language, case_name: str) -> str:
    generator = JAVA if language is Language.JAVA else KOTLIN
    return generator.generate(CASES[case_name].meta)


def stub_of(generator, *params: tuple[str, str], returns: str) -> str:
    declared = tuple(Param(name, parse_value_type(text)) for name, text in params)
    signature = FunctionSignature("solve", declared, Returns(parse_value_type(returns)))
    return generator.generate(replace(CASES["two-sum"].meta, signature=signature))


def with_many_params(case: StubCase, count: int) -> StubCase:
    params = tuple(
        Param(f"parameterNumber{index}", ScalarType(Scalar.STRING)) for index in range(count)
    )
    signature = FunctionSignature("combine", params, Returns(ScalarType(Scalar.INT)))
    return replace(case, meta=replace(case.meta, signature=signature))


@stub_cases
def test_java_stub_matches_its_golden(stub_case: StubCase) -> None:
    check_stub(Language.JAVA, stub_case, JAVA.generate(stub_case.meta))


@stub_cases
def test_kotlin_stub_matches_its_golden(stub_case: StubCase) -> None:
    check_stub(Language.KOTLIN, stub_case, KOTLIN.generate(stub_case.meta))


@pytest.mark.parametrize(
    ("language", "case_name", "example"),
    [
        (Language.JAVA, "two-sum", TWO_SUM_JAVA),
        (Language.KOTLIN, "two-sum", TWO_SUM_KOTLIN),
        (Language.JAVA, "lru-cache", LRU_CACHE_JAVA),
        (Language.KOTLIN, "lru-cache", LRU_CACHE_KOTLIN),
    ],
)
def test_stub_below_the_header_is_the_worked_example(language, case_name, example):
    _header, _blank, body = generated(language, case_name).split("\n", 2)
    assert body == example


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_header_names_title_statement_and_run_command(language):
    assert generated(language, "two-sum").startswith(TWO_SUM_HEADER)


def test_java_header_longer_than_the_column_limit_puts_the_run_command_on_its_own_line():
    lines = generated(Language.JAVA, "merge-k-lists").splitlines()
    assert lines[:2] == [
        "// Merge k Sorted Lists. Statement: .statements/merge-k-sorted-lists.md.",
        "// Run: cstudy test merge-k-sorted-lists",
    ]


def test_java_imports_support_classes_only_when_used():
    assert "import cs.support.*;\nimport java.util.*;\n" in generated(Language.JAVA, "clone-graph")


def test_java_imports_big_decimal_and_local_date_between_support_and_util():
    stub = stub_of(JAVA, ("head", "ListNode"), ("amount", "decimal"), returns="date[]")
    imports = [line for line in stub.splitlines() if line.startswith("import ")]
    assert imports == [
        "import cs.support.*;",
        "import java.math.BigDecimal;",
        "import java.time.LocalDate;",
        "import java.util.*;",
    ]


def test_java_imports_only_the_decimal_and_date_types_in_use():
    only_decimal = stub_of(JAVA, ("amount", "list<decimal>"), returns="int")
    only_date = stub_of(JAVA, ("day", "date"), returns="int")
    assert "import java.math.BigDecimal;\nimport java.util.*;\n" in only_decimal
    assert "import java.time.LocalDate;\nimport java.util.*;\n" in only_date
    assert "LocalDate" not in only_decimal
    assert "BigDecimal" not in only_date


def test_kotlin_imports_big_decimal_and_local_date_after_support():
    stub = stub_of(KOTLIN, ("head", "ListNode"), ("amount", "decimal"), returns="date")
    imports = [line for line in stub.splitlines() if line.startswith("import ")]
    assert imports == [
        "import cs.support.*",
        "import java.math.BigDecimal",
        "import java.time.LocalDate",
    ]


def test_kotlin_imports_only_the_decimal_and_date_types_in_use():
    only_decimal = stub_of(KOTLIN, ("amount", "decimal[]"), returns="int")
    only_date = stub_of(KOTLIN, ("day", "date"), returns="int")
    assert "\nimport java.math.BigDecimal\n\nclass" in only_decimal
    assert "\nimport java.time.LocalDate\n\nclass" in only_date


def test_java_omits_support_import_without_nodes():
    assert "cs.support" not in generated(Language.JAVA, "two-sum")


def test_kotlin_imports_support_classes_only_when_used():
    assert "\nimport cs.support.*\n\nclass Solution {" in generated(Language.KOTLIN, "invert-tree")


def test_kotlin_omits_imports_without_nodes():
    assert "import" not in generated(Language.KOTLIN, "lru-cache")


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_progressive_methods_carry_level_comments(language):
    text = generated(language, "progressive")
    assert [line.strip() for line in text.splitlines() if "Level" in line] == [
        "// Level 1",
        "// Level 1",
        "// Level 2",
    ]


def test_java_wraps_a_signature_longer_than_the_column_limit():
    text = JAVA.generate(with_many_params(CASES["two-sum"], 6).meta)
    assert max(len(line) for line in text.splitlines()) <= JAVA_LINE_LIMIT


def test_java_wrapped_signature_puts_one_parameter_per_line():
    text = JAVA.generate(with_many_params(CASES["two-sum"], 6).meta)
    assert "    public int combine(\n            String parameterNumber0,\n" in text


def test_kotlin_wraps_a_signature_longer_than_the_column_limit():
    text = KOTLIN.generate(with_many_params(CASES["two-sum"], 8).meta)
    assert max(len(line) for line in text.splitlines()) <= KOTLIN_LINE_LIMIT


def test_kotlin_wrapped_signature_uses_trailing_comma():
    text = KOTLIN.generate(with_many_params(CASES["two-sum"], 8).meta)
    assert "        parameterNumber7: String,\n    ): Int {\n" in text


@pytest.mark.parametrize(("dsl", "java", "_kotlin"), MAPPING_TABLE, ids=lambda row: row)
def test_java_type_follows_the_mapping_table(dsl, java, _kotlin):
    assert java_type(parse_value_type(dsl)) == java


@pytest.mark.parametrize(("dsl", "_java", "kotlin"), MAPPING_TABLE, ids=lambda row: row)
def test_kotlin_type_follows_the_mapping_table(dsl, _java, kotlin):
    assert kotlin_type(parse_value_type(dsl)) == kotlin


def test_nested_lists_map_element_wise():
    nested = parse_value_type("list<list<list<int>>>")
    assert (java_type(nested), kotlin_type(nested)) == (
        "List<List<List<Integer>>>",
        "List<List<List<Int>>>",
    )
