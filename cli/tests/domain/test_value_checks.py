import pytest

from coding_study.domain.cases import (
    Case,
    Expected,
    FunctionInput,
    GeneratedInput,
    OperationSequence,
)
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    NodeSerialization,
    Param,
    Returns,
)
from coding_study.domain.type_dsl import VoidType, parse_return_type, parse_value_type
from coding_study.domain.value_checks import case_issues, input_value_issues, output_value_issues


def typed(text: str):
    return parse_value_type(text)


@pytest.mark.parametrize(
    ("type_text", "value"),
    [
        ("int", 0),
        ("int", -(2**31)),
        ("int", 2**31 - 1),
        ("long", 2**53 - 1),
        ("long", -(2**53 - 1)),
        ("double", 1.5),
        ("double", 2),
        ("bool", True),
        ("string", ""),
        ("char", "a"),
        ("int[]", [1, 2]),
        ("int[][]", [[1], []]),
        ("char[]", ["a", "b"]),
        ("decimal", "0"),
        ("decimal", "2500.00"),
        ("decimal", "-0.50"),
        ("decimal", "0.0"),
        ("decimal", "-0"),
        ("decimal", "9999999999999999999999999999"),
        ("decimal", "0.0000000000000000000000000001"),
        ("decimal", "0." + "0" * 28),
        ("decimal[]", ["1", "2.50", "-3"]),
        ("decimal[][]", [["1.5"], []]),
        ("list<decimal>", ["10.00", "0.1"]),
        ("date", "2024-02-29"),
        ("date", "0001-01-01"),
        ("date", "9999-12-31"),
        ("date[]", ["2024-01-01", "2024-12-31"]),
        ("date[][]", [["2024-01-01"], []]),
        ("list<date>", ["2023-02-28"]),
        ("list<list<string>>", [["a"], []]),
        ("list<int[]>", [[1, 2]]),
        ("ListNode", []),
        ("ListNode", [1, 2, 3]),
        ("ListNode", {"values": [3, 2, 0, -4], "cycle_at": 1}),
        ("TreeNode", [3, 9, 20, None, None, 15, 7]),
        ("TreeNode", []),
        ("GraphNode", [[2, 4], [1, 3], [2, 4], [1, 3]]),
        ("GraphNode", [[]]),
        ("GraphNode", []),
        ("ListNode[]", [[1, 4], [], [2]]),
        ("list<TreeNode>", [[1, None, 2], []]),
    ],
)
def test_valid_inputs(type_text, value):
    assert input_value_issues(value, typed(type_text)) == []


@pytest.mark.parametrize(
    ("type_text", "value", "message"),
    [
        ("int", 2**31, "outside the int range"),
        ("int", 1.5, "expected int"),
        ("int", True, "expected int"),
        ("long", 2**53, "beyond 2^53-1"),
        ("double", True, "expected double"),
        ("double", "1", "expected double"),
        ("bool", 1, "expected bool"),
        ("string", 3, "expected string"),
        ("char", "ab", "expected one character"),
        ("char", "😀", "outside the BMP"),
        ("decimal", 2500, "expected decimal, got 2500"),
        ("decimal", 2500.5, "expected decimal, got 2500.5"),
        ("decimal", True, "expected decimal"),
        ("decimal", None, "expected decimal, got null"),
        ("decimal", "007", "not a decimal"),
        ("decimal", "00.5", "not a decimal"),
        ("decimal", "1e3", "not a decimal"),
        ("decimal", ".5", "not a decimal"),
        ("decimal", "5.", "not a decimal"),
        ("decimal", "+5", "not a decimal"),
        ("decimal", " 5", "not a decimal"),
        ("decimal", "1,000", "not a decimal"),
        ("decimal", "NaN", "not a decimal"),
        ("decimal", "-", "not a decimal"),
        ("decimal", "\uff11\uff12", "not a decimal"),
        ("decimal", "1" * 29, "more than 28 significant digits"),
        ("decimal", "0." + "1" * 29, "more than 28 significant digits"),
        ("decimal", "0." + "0" * 28 + "1", "more than 28 digits after the point"),
        ("decimal", "0." + "0" * 29, "more than 28 digits after the point"),
        ("decimal[]", ["1", 2], "[1]: expected decimal, got 2"),
        ("date", 20240101, "expected date, got 20240101"),
        ("date", "20240101", "not a date"),
        ("date", "2024-1-1", "not a date"),
        ("date", "2024/01/01", "not a date"),
        ("date", "2024-01-01T00:00:00", "not a date"),
        ("date", "\uff12\uff10\uff12\uff14-01-01", "not a date"),
        ("date", "2023-02-29", "not a calendar day"),
        ("date", "2024-13-01", "not a calendar day"),
        ("date", "2024-04-31", "not a calendar day"),
        ("date", "0000-01-01", "not a calendar day"),
        ("date[]", ["2024-01-01", "soon"], "[1]: "),
        ("int[]", 1, "expected an array"),
        ("int[]", [1, "2"], "[1]: expected int"),
        ("ListNode", [1, None], "[1]: expected int"),
        ("ListNode", {"values": [1], "cycle_at": 1}, "cycle_at"),
        ("ListNode", {"values": [1]}, "cycle_at"),
        ("TreeNode", [None, 1], "root"),
        ("TreeNode", ["a"], "[0]: expected int"),
        ("GraphNode", [[2]], "neighbor 2"),
        ("GraphNode", [1], "[0]: expected an array"),
    ],
)
def test_invalid_inputs(type_text, value, message):
    issues = input_value_issues(value, typed(type_text))
    assert any(message in issue for issue in issues), issues


@pytest.mark.parametrize(
    ("type_text", "value"),
    [
        ("decimal", "0"),
        ("decimal", "2500"),
        ("decimal", "-0.5"),
        ("decimal", "1234.0625"),
        ("decimal", "100"),
        ("decimal[]", ["1", "2.5"]),
        ("list<decimal>", ["0.01"]),
        ("date", "2024-02-29"),
        ("list<date>", ["2024-01-01"]),
    ],
)
def test_canonical_expected_decimals_and_dates_are_valid(type_text, value):
    assert output_value_issues(value, typed(type_text)) == []


@pytest.mark.parametrize(
    ("value", "canonical"),
    [
        ("2500.00", "2500"),
        ("2500.50", "2500.5"),
        ("0.0", "0"),
        ("-0", "0"),
        ("-0.00", "0"),
        ("10.10", "10.1"),
    ],
)
def test_expected_decimals_must_be_canonical_and_the_message_names_the_form(value, canonical):
    assert output_value_issues(value, typed("decimal")) == [
        f'"{value}" is not canonical (no trailing fractional zeros, no "-0"): write "{canonical}"'
    ]


def test_the_canonical_form_applies_to_every_decimal_in_an_expected_list():
    issues = output_value_issues(["1", "2.0"], typed("list<decimal>"))
    assert issues == [
        '[1]: "2.0" is not canonical (no trailing fractional zeros, no "-0"): write "2"'
    ]


def test_inputs_keep_their_scale_so_a_non_canonical_input_is_valid():
    assert input_value_issues("2500.00", typed("decimal")) == []


def test_invalid_expected_decimals_report_the_shape_before_canonical_form():
    assert output_value_issues(2500, typed("decimal")) == [
        "expected decimal, got 2500 (decimals are JSON strings)"
    ]


def test_expected_dates_are_checked_like_input_dates():
    issues = output_value_issues("2023-02-29", typed("date"))
    assert issues == ['"2023-02-29" is not a calendar day (years 0001 to 9999)']


def test_outputs_never_contain_cycles():
    value = {"values": [1, 2], "cycle_at": 0}
    assert output_value_issues(value, typed("ListNode")) != []


def test_expected_trees_have_trailing_nulls_trimmed():
    assert output_value_issues([1, None], typed("TreeNode")) == [
        "trailing null (serialized trees trim them)"
    ]


TWO_SUM = FunctionSignature(
    "twoSum",
    (Param("nums", typed("int[]")), Param("target", typed("int"))),
    Returns(parse_return_type("int[]")),
)


def function_case(arguments, expected=None) -> Case:
    return Case(
        "h1", FunctionInput(arguments), Expected(expected) if expected is not None else None
    )


def test_valid_function_case():
    case = function_case({"nums": [1, 2], "target": 3}, [0, 1])
    assert case_issues(TWO_SUM, case) == ()


def test_missing_argument():
    assert case_issues(TWO_SUM, function_case({"nums": [1]})) == ('input: missing "target"',)


def test_unknown_argument():
    case = function_case({"nums": [1], "target": 1, "extra": 2})
    assert case_issues(TWO_SUM, case) == ('input: unknown parameter "extra"',)


def test_argument_type_is_checked():
    case = function_case({"nums": [1, 2.5], "target": 3})
    assert case_issues(TWO_SUM, case) == ("input.nums[1]: expected int, got 2.5",)


def test_expected_type_is_checked():
    case = function_case({"nums": [1], "target": 1}, "x")
    assert case_issues(TWO_SUM, case) == ('expected: expected an array, got "x"',)


def test_generated_cases_have_no_values_to_check():
    assert case_issues(TWO_SUM, Case("g1", GeneratedInput(10, 1))) == ()


def test_function_problems_need_inputs_not_operations():
    case = Case("h1", OperationSequence(("X",), ((),)), Expected([None]))
    assert case_issues(TWO_SUM, case) == ("a function problem's cases need input, not ops",)


def test_void_returns_expect_null():
    signature = FunctionSignature("noop", (), Returns(VoidType()))
    assert case_issues(signature, function_case({}, 1)) == ("expected: void returns expect null",)


def test_output_from_expects_the_parameter_type():
    signature = FunctionSignature(
        "sortValues", (Param("values", typed("int[]")),), Returns(VoidType(), output_from="values")
    )
    assert case_issues(signature, function_case({"values": [2, 1]}, [1, 2])) == ()


def test_as_value_expects_a_node_value():
    signature = FunctionSignature(
        "middle",
        (Param("head", typed("ListNode")),),
        Returns(typed("ListNode"), serialize_as=NodeSerialization.VALUE),
    )
    assert case_issues(signature, function_case({"head": [1, 2]}, [2])) == (
        "expected: expected int or null, got [2]",
    )


def test_ref_of_must_name_a_value_in_the_referenced_structure():
    signature = FunctionSignature(
        "pick",
        (Param("head", typed("ListNode")), Param("node", typed("ListNode"), ref_of="head")),
        Returns(typed("ListNode")),
    )
    case = function_case({"head": [1, 2], "node": 5}, [])
    assert case_issues(signature, case) == ("input.node: 5 is not a value in head",)


LRU = ClassSignature(
    "LRUCache",
    (Param("capacity", typed("int")),),
    (
        Method("get", (Param("key", typed("int")),), Returns(typed("int"))),
        Method(
            "put", (Param("key", typed("int")), Param("value", typed("int"))), Returns(VoidType())
        ),
    ),
)


def ops_case(ops, args, expected) -> Case:
    return Case("ex1", OperationSequence(tuple(ops), tuple(map(tuple, args))), Expected(expected))


def test_valid_operation_sequence():
    case = ops_case(["LRUCache", "put", "get"], [[2], [1, 1], [1]], [None, None, 1])
    assert case_issues(LRU, case) == ()


def test_first_operation_is_the_constructor():
    case = ops_case(["Cache", "get"], [[2], [1]], [None, 1])
    assert case_issues(LRU, case) == ('ops[0]: expected the class name "LRUCache"',)


def test_unknown_method():
    case = ops_case(["LRUCache", "evict"], [[2], []], [None, None])
    assert case_issues(LRU, case) == ('ops[1]: no method "evict"',)


def test_arity_is_checked():
    case = ops_case(["LRUCache", "put"], [[2], [1]], [None, None])
    assert case_issues(LRU, case) == ("args[1]: put takes 2 arguments, got 1",)


def test_constructor_arity_is_checked():
    case = ops_case(["LRUCache"], [[]], [None])
    assert case_issues(LRU, case) == ("args[0]: LRUCache takes 1 argument, got 0",)


def test_argument_types_are_checked():
    case = ops_case(["LRUCache", "get"], [[2], ["k"]], [None, -1])
    assert case_issues(LRU, case) == ('args[1][0]: expected int, got "k"',)


def test_one_expected_value_per_operation():
    case = ops_case(["LRUCache", "get"], [[2], [1]], [None])
    assert case_issues(LRU, case) == ("expected: 1 values for 2 operations",)


def test_constructor_expects_null():
    case = ops_case(["LRUCache"], [[2]], [1])
    assert case_issues(LRU, case) == ("expected[0]: the constructor expects null",)


def test_operation_results_are_typed():
    case = ops_case(["LRUCache", "put", "get"], [[2], [1, 1], [1]], [None, 1, "one"])
    assert case_issues(LRU, case) == (
        "expected[1]: void returns expect null",
        'expected[2]: expected int, got "one"',
    )


def test_class_problems_need_operations():
    case = function_case({"capacity": 1}, None)
    assert case_issues(LRU, case) == ("a class problem's cases need ops and args, not input",)


MESSAGE_LOG = ClassSignature(
    "MessageLog",
    (Param("visibilityMs", typed("long")),),
    (
        Method(
            "publish",
            (Param("body", typed("string")),),
            Returns(typed("long")),
            level=1,
            is_async=True,
        ),
        Method(
            "receive",
            (Param("waitMs", typed("long")),),
            Returns(typed("string")),
            level=2,
            is_async=True,
        ),
        Method("clear", (), Returns(VoidType()), level=1),
    ),
)


# harness operations


def test_the_virtual_clock_example_of_the_format_conforms():
    case = ops_case(
        ["MessageLog", "@spawn", "@advance", "publish", "@join", "@now", "receive", "@now"],
        [[30000], ["r1", "receive", 5000], [1000], ["a"], ["r1"], [], [2000], []],
        [None, None, None, 1, "a", 1000, "", 3000],
    )
    assert case_issues(MESSAGE_LOG, case) == ()


def test_a_joined_void_method_expects_null():
    case = ops_case(
        ["MessageLog", "@spawn", "@join"], [[1], ["c", "clear"], ["c"]], [None, None, None]
    )
    assert case_issues(MESSAGE_LOG, case) == ()


def test_advance_takes_one_integer():
    case = ops_case(["MessageLog", "@advance"], [[1], ["1000"]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ('args[1][0]: expected long, got "1000"',)


def test_advance_takes_no_fraction():
    case = ops_case(["MessageLog", "@advance"], [[1], [2.5]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1][0]: expected long, got 2.5",)


def test_advance_arity_is_checked():
    case = ops_case(["MessageLog", "@advance"], [[1], []], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1]: @advance takes 1 argument, got 0",)


def test_advance_leaves_its_range_to_the_clock_check():
    case = ops_case(["MessageLog", "@advance", "@advance"], [[1], [0], [-5]], [None, None, None])
    assert case_issues(MESSAGE_LOG, case) == ()


@pytest.mark.parametrize("operation", ["@advance", "@spawn"])
def test_advance_and_spawn_expect_null(operation):
    arguments = [1000] if operation == "@advance" else ["r1", "clear"]
    case = ops_case(["MessageLog", operation], [[1], arguments], [None, 5])
    assert case_issues(MESSAGE_LOG, case) == (f"expected[1]: {operation} expects null",)


def test_spawn_calls_a_method_with_its_arguments():
    case = ops_case(["MessageLog", "@spawn"], [[1], ["r1", "receive", 5000]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ()


def test_spawn_names_a_task_a_method_and_the_call():
    case = ops_case(["MessageLog", "@spawn"], [[1], ["r1"]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == (
        "args[1]: @spawn takes a task, a method and its arguments",
    )


def test_the_task_of_a_spawn_is_a_string():
    case = ops_case(["MessageLog", "@spawn"], [[1], [5, "clear"]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1][0]: expected a task name (string), got 5",)


def test_the_task_of_a_spawn_is_not_empty():
    case = ops_case(["MessageLog", "@spawn"], [[1], ["", "clear"]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1][0]: a task name is not empty",)


def test_the_method_of_a_spawn_is_a_string():
    case = ops_case(["MessageLog", "@spawn"], [[1], ["r1", 7]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1][1]: expected a method name (string), got 7",)


def test_the_method_of_a_spawn_exists():
    case = ops_case(["MessageLog", "@spawn"], [[1], ["r1", "evict"]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ('args[1][1]: no method "evict"',)


def test_the_arguments_of_a_spawn_are_the_methods():
    case = ops_case(["MessageLog", "@spawn"], [[1], ["r1", "receive"]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1]: receive takes 1 argument, got 0",)


def test_the_arguments_of_a_spawn_are_typed_by_the_method():
    case = ops_case(["MessageLog", "@spawn"], [[1], ["r1", "receive", "soon"]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ('args[1][2]: expected long, got "soon"',)


def test_join_takes_one_task():
    case = ops_case(["MessageLog", "@join"], [[1], []], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1]: @join takes 1 argument, got 0",)


def test_the_task_of_a_join_is_a_string():
    case = ops_case(["MessageLog", "@join"], [[1], [4]], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ("args[1][0]: expected string, got 4",)


def test_a_join_expects_the_result_of_the_method_its_task_called():
    case = ops_case(
        ["MessageLog", "@spawn", "@join"], [[1], ["r1", "receive", 10], ["r1"]], [None, None, 7]
    )
    assert case_issues(MESSAGE_LOG, case) == ("expected[2]: expected string, got 7",)


def test_a_join_of_a_void_method_expects_null():
    case = ops_case(
        ["MessageLog", "@spawn", "@join"], [[1], ["c", "clear"], ["c"]], [None, None, 1]
    )
    assert case_issues(MESSAGE_LOG, case) == ("expected[2]: void returns expect null",)


def test_a_join_of_a_task_nobody_spawned_has_no_type_to_check():
    case = ops_case(["MessageLog", "@join"], [[1], ["ghost"]], [None, "anything"])
    assert case_issues(MESSAGE_LOG, case) == ()


def test_now_takes_no_arguments():
    case = ops_case(["MessageLog", "@now"], [[1], [0]], [None, 0])
    assert case_issues(MESSAGE_LOG, case) == ("args[1]: @now takes 0 arguments, got 1",)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("soon", 'expected long, got "soon"'),
        (1.5, "expected long, got 1.5"),
        (None, "expected long, got null"),
        (2**53, "beyond 2^53-1"),
    ],
)
def test_now_expects_an_integer(value, message):
    case = ops_case(["MessageLog", "@now"], [[1], []], [None, value])
    [issue] = case_issues(MESSAGE_LOG, case)
    assert message in issue


def test_now_may_expect_zero():
    case = ops_case(["MessageLog", "@now"], [[1], []], [None, 0])
    assert case_issues(MESSAGE_LOG, case) == ()


def test_an_unknown_harness_operation_is_named_as_one():
    case = ops_case(["MessageLog", "@settle"], [[1], []], [None, None])
    assert case_issues(MESSAGE_LOG, case) == ('ops[1]: no harness operation "@settle"',)
