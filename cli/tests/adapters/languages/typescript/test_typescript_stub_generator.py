from coding_study.adapters.languages.typescript import create_stub_generator
from coding_study.adapters.languages.typescript.stub_generator import typescript_type
from coding_study.domain.problem import Language
from coding_study.domain.type_dsl import parse_return_type
from tests.stub_contract import STUB_CASES, StubCase, check_stub, stub_cases

TWO_SUM_SPEC_EXAMPLE = """\
// Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum
export function twoSum(nums: number[], target: number): number[] {
  throw new Error("Not implemented");
}
"""

LRU_CACHE_HEADER = "// LRU Cache. Statement: .statements/lru-cache.md. Run: cstudy test lru-cache\n"
LRU_CACHE_SPEC_EXAMPLE = """\
export class LRUCache {
  constructor(capacity: number) {}

  get(key: number): number {
    throw new Error("Not implemented");
  }

  put(key: number, value: number): void {
    throw new Error("Not implemented");
  }
}
"""


def generate(case_name: str) -> str:
    case = next(case for case in STUB_CASES if case.name == case_name)
    return create_stub_generator().generate(case.meta)


@stub_cases
def test_typescript_stub_matches_its_golden(stub_case: StubCase) -> None:
    check_stub(Language.TYPESCRIPT, stub_case, create_stub_generator().generate(stub_case.meta))


def test_two_sum_stub_is_the_spec_example():
    assert generate("two-sum") == TWO_SUM_SPEC_EXAMPLE


def test_lru_cache_stub_is_the_spec_example_after_the_header():
    # The spec's lru-cache example omits the header line that every stub carries.
    assert generate("lru-cache") == LRU_CACHE_HEADER + LRU_CACHE_SPEC_EXAMPLE


def test_imports_only_the_support_classes_the_signature_uses():
    assert 'import { TreeNode } from "#support";\n' in generate("invert-tree")


def test_imports_support_classes_in_spec_order():
    assert 'import { ListNode, TreeNode, GraphNode } from "#support";\n' in generate(
        "conformance-types"
    )


def test_omits_the_import_when_no_support_class_is_used():
    assert "#support" not in generate("two-sum")


def test_wraps_a_signature_wider_than_80_columns_with_trailing_commas():
    assert (
        "export function getHTTPCode(\n"
        "  maxValue: number,\n"
        "  userID: string,\n"
        "  utf8Text: string,\n"
        "): number {\n"
    ) in generate("naming")


def test_marks_each_progressive_method_with_its_level():
    assert "  // Level 2\n  scanByPrefix(" in generate("progressive")


def test_void_function_with_output_from_returns_void():
    assert "export function rotate(nums: number[], k: number): void {\n" in generate("rotate")


def test_maps_node_elements_to_nullable_parenthesized_arrays():
    assert typescript_type(parse_return_type("ListNode[]")) == "(ListNode | null)[]"


def test_maps_nested_lists_to_nested_arrays():
    assert typescript_type(parse_return_type("list<list<list<int>>>")) == "number[][][]"


def test_maps_list_of_int_arrays_to_a_matrix():
    assert typescript_type(parse_return_type("list<int[]>")) == "number[][]"


def test_maps_char_to_string():
    assert typescript_type(parse_return_type("char[][]")) == "string[][]"


def test_maps_bool_to_boolean():
    assert typescript_type(parse_return_type("list<bool>")) == "boolean[]"
