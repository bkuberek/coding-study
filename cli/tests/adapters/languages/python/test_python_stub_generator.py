from dataclasses import replace

import pytest

from coding_study.adapters.languages.python import create_stub_generator
from coding_study.adapters.languages.python.stub_generator import LINE_LENGTH, python_type
from coding_study.domain.concurrency import ConcurrencyModel
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    Returns,
)
from coding_study.domain.type_dsl import parse_return_type, parse_value_type
from tests.stub_contract import STUB_CASES, StubCase, check_stub, stub_cases

GENERATOR = create_stub_generator()
TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
LRU_CACHE = next(case.meta for case in STUB_CASES if case.name == "lru-cache")


def function_meta(
    *params: tuple[str, str], returns: str = "int", name: str = "solve"
) -> ProblemMeta:
    declared = tuple(Param(param, parse_value_type(type_text)) for param, type_text in params)
    signature = FunctionSignature(name, declared, Returns(parse_return_type(returns)))
    return replace(TWO_SUM, signature=signature)


def stub_lines(meta: ProblemMeta) -> list[str]:
    return GENERATOR.generate(meta).splitlines()


@stub_cases
def test_python_stub_matches_its_golden(stub_case: StubCase):
    check_stub(Language.PYTHON, stub_case, GENERATOR.generate(stub_case.meta))


@pytest.mark.parametrize(
    ("type_text", "expected"),
    [
        ("int", "int"),
        ("long", "int"),
        ("double", "float"),
        ("bool", "bool"),
        ("string", "str"),
        ("char", "str"),
        ("char[]", "list[str]"),
        ("decimal", "Decimal"),
        ("date", "date"),
        ("decimal[]", "list[Decimal]"),
        ("date[][]", "list[list[date]]"),
        ("list<decimal>", "list[Decimal]"),
        ("list<date>", "list[date]"),
        ("double[][]", "list[list[float]]"),
        ("list<long>", "list[int]"),
        ("list<int[]>", "list[list[int]]"),
        ("list<list<list<int>>>", "list[list[list[int]]]"),
        ("ListNode", "ListNode | None"),
        ("ListNode[]", "list[ListNode | None]"),
        ("list<TreeNode>", "list[TreeNode | None]"),
    ],
)
def test_maps_dsl_types_to_python_annotations(type_text, expected):
    assert python_type(parse_value_type(type_text)) == expected


def test_void_maps_to_none():
    assert python_type(parse_return_type("void")) == "None"


def test_header_names_title_statement_and_run_command():
    assert stub_lines(TWO_SUM)[0] == (
        '"""Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum"""'
    )


def test_header_keeps_a_title_that_already_ends_a_sentence():
    meta = replace(TWO_SUM, title="Is It Sorted?")
    assert stub_lines(meta)[0].startswith('"""Is It Sorted? Statement:')


def test_header_escapes_quotes_in_the_title():
    meta = replace(TWO_SUM, title='Say "Hi"')
    assert stub_lines(meta)[0].startswith('"""Say \\"Hi\\". Statement:')


def test_stub_without_node_types_imports_nothing():
    assert not any(line.startswith("from ") for line in stub_lines(TWO_SUM))


def test_imports_only_the_node_classes_in_use_sorted():
    meta = function_meta(("root", "TreeNode"), ("lists", "ListNode[]"), returns="TreeNode")
    assert "from cs_support import ListNode, TreeNode" in stub_lines(meta)


def test_imports_the_decimal_and_date_types_in_use_from_the_standard_library():
    meta = function_meta(("amounts", "list<decimal>"), ("day", "date"), returns="decimal")
    assert stub_lines(meta)[2:6] == [
        "from datetime import date",
        "from decimal import Decimal",
        "",
        "",
    ]


def test_imports_only_decimal_when_only_decimal_is_used():
    meta = function_meta(("amount", "decimal[][]"), returns="int")
    assert stub_lines(meta)[2:5] == ["from decimal import Decimal", "", ""]


def test_imports_only_date_when_only_date_is_used():
    meta = function_meta(("day", "int"), returns="date[]")
    assert stub_lines(meta)[2:5] == ["from datetime import date", "", ""]


def test_standard_library_imports_come_before_the_support_import_in_their_own_block():
    meta = function_meta(("amount", "decimal"), ("head", "ListNode"), returns="date")
    assert stub_lines(meta)[2:7] == [
        "from datetime import date",
        "from decimal import Decimal",
        "",
        "from cs_support import ListNode",
        "",
    ]


def test_function_names_and_parameters_are_snake_case():
    meta = function_meta(("maxValue", "int"), name="getHTTPCode")
    assert "def get_http_code(max_value: int) -> int:" in stub_lines(meta)


def test_constructor_never_raises():
    lines = stub_lines(LRU_CACHE)
    constructor = lines.index("    def __init__(self, capacity: int) -> None:")
    assert lines[constructor + 1] == "        pass"


def test_progressive_methods_carry_their_level():
    method = Method("scan", (), Returns(parse_return_type("int")), level=2)
    meta = replace(LRU_CACHE, signature=ClassSignature("Db", (), (method,)))
    lines = stub_lines(meta)
    assert lines[lines.index("    def scan(self) -> int:") - 1] == "    # Level 2"


def test_a_long_signature_puts_parameters_on_their_own_line():
    matrix = "list<list<double>>"
    meta = function_meta(("firstNumbers", matrix), ("secondNumbers", matrix), returns=matrix)
    assert stub_lines(meta)[3:6] == [
        "def solve(",
        "    first_numbers: list[list[float]], second_numbers: list[list[float]]",
        ") -> list[list[float]]:",
    ]


def test_parameters_too_long_for_one_line_get_one_line_each():
    params = [(f"parameterNumber{index}", "list<list<string>>") for index in range(4)]
    lines = stub_lines(function_meta(*params))
    assert lines[4:9] == [
        *(f"    parameter_number{index}: list[list[str]]," for index in range(4)),
        ") -> int:",
    ]


def test_no_generated_line_exceeds_the_line_length():
    longest = max(
        len(line)
        for case in STUB_CASES
        for line in GENERATOR.generate(case.meta).splitlines()
        if not line.startswith('"""')
    )
    assert longest <= LINE_LENGTH


BOUNDED_QUEUE = next(case.meta for case in STUB_CASES if case.name == "bounded-blocking-queue")


def async_queue() -> ProblemMeta:
    concurrency = replace(
        BOUNDED_QUEUE.concurrency,  # type: ignore[arg-type]
        models={Language.PYTHON: ConcurrencyModel.ASYNC},
    )
    return replace(BOUNDED_QUEUE, concurrency=concurrency)


def test_async_model_makes_blocking_methods_async():
    lines = stub_lines(async_queue())
    assert [line.strip() for line in lines if "def " in line][1:] == [
        "async def put(self, value: int) -> None:",
        "async def take(self) -> int:",
        "def size(self) -> int:",
    ]


def test_async_model_is_named_in_the_header():
    assert "Concurrency: async" in stub_lines(async_queue())
