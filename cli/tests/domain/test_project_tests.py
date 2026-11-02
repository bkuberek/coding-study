"""The generated test file of one level, before a language spells it
(docs/specs/problem-format.md#generated-test-files)."""

from dataclasses import replace

import pytest

from coding_study.domain.cases import Case, Expected, FunctionInput
from coding_study.domain.problem import (
    ComparatorSpec,
    ComparatorType,
    Language,
    Level,
    ProblemKind,
)
from coding_study.domain.project_tests import (
    HARNESS_TEST_LANGUAGES,
    Advance,
    Call,
    Join,
    LevelTest,
    Now,
    Spawn,
    level_tests,
)
from coding_study.domain.signature import ClassSignature
from coding_study.domain.virtual_clock import ProjectClock
from tests.project_builders import (
    BANK,
    CREATE_ACCOUNT,
    DEPOSIT,
    TRANSFER,
    method,
    ops_case,
    project_meta,
    project_problem,
)

EX1 = ops_case(
    "ex1",
    1,
    ("createAccount", [1, "ivy"], True),
    ("deposit", [2, "ivy", 800], 800),
    note="deposits add up",
)
EX2 = ops_case("ex2", 1, ("deposit", [1, "max", 50], -1))
HIDDEN = ops_case("h1", 1, ("deposit", [1, "ann", 5], -1), visible=False)
LEVEL_2 = ops_case("ex3", 2, ("transfer", [3, "ivy", "leo", 200], -1))
PROBLEM = project_problem(EX1, HIDDEN, LEVEL_2, EX2)


def generated(problem=PROBLEM, level: int = 1) -> tuple[LevelTest, ...]:
    return level_tests(problem, level).tests


def with_comparator(**per_method: ComparatorType):
    comparator = ComparatorSpec(ComparatorType.OPS, tolerance=1e-4, per_method=per_method)
    return project_problem(EX1, meta=project_meta(comparator=comparator))


def test_a_level_has_one_test_per_visible_case_in_tests_json_order():
    assert [test.case_id for test in generated()] == ["ex1", "ex2"]


def test_a_later_level_has_only_its_own_cases():
    assert [test.case_id for test in generated(level=2)] == ["ex3"]


def test_a_test_keeps_the_case_note():
    assert generated()[0].note == "deposits add up"


def test_a_test_builds_the_class_with_the_constructor_arguments():
    case = ops_case("ex1", 1, ("deposit", [1, "a", 1], -1), constructor=[10, "eur"])
    assert generated(project_problem(case))[0].constructor_arguments == (10, "eur")


def test_each_operation_after_the_constructor_is_a_call_with_its_expected_output():
    assert generated()[0].calls == (
        Call(CREATE_ACCOUNT, (1, "ivy"), True, ComparatorType.EXACT),
        Call(DEPOSIT, (2, "ivy", 800), 800, ComparatorType.EXACT),
    )


def test_a_method_compares_with_its_per_method_comparator():
    problem = with_comparator(deposit=ComparatorType.FLOAT)
    assert [call.comparator for call in generated(problem)[0].calls] == [
        ComparatorType.EXACT,
        ComparatorType.FLOAT,
    ]


def test_the_float_tolerance_comes_from_the_comparator():
    assert level_tests(with_comparator(), 1).tolerance == 1e-4


@pytest.mark.parametrize(
    "comparator", [ComparatorType.UNORDERED_NESTED, ComparatorType.CHECKER, ComparatorType.OPS]
)
def test_a_comparator_a_generated_test_cannot_express_is_rejected(comparator):
    with pytest.raises(ValueError, match=f"cannot compare deposit with {comparator}"):
        level_tests(with_comparator(deposit=comparator), 1)


def test_a_call_to_a_void_method_checks_nothing():
    reset = method("reset", 1, "timestamp: long")
    signature = ClassSignature("Bank", (), (*BANK.methods, reset))
    case = ops_case("ex1", 1, ("reset", [1], None))
    problem = project_problem(case, meta=project_meta(signature=signature))
    assert not generated(problem)[0].calls[0].returns_value


def test_a_call_to_a_method_with_a_result_checks_it():
    assert generated()[0].calls[0].returns_value


def test_the_file_is_the_level_test_file_of_the_project_language():
    assert level_tests(PROBLEM, 2).path == "tests/test_level_2.py"


def test_a_typescript_project_writes_its_own_file():
    problem = project_problem(EX1, meta=project_meta(language=Language.TYPESCRIPT))
    assert level_tests(problem, 1).path == "tests/level-1.test.ts"


def test_level_1_is_written_when_the_attempt_starts():
    assert level_tests(PROBLEM, 1).title == (
        "Level 1 examples of bank-project-python, written by `cstudy start`."
    )


def test_a_later_level_is_written_when_a_submission_opens_it():
    assert level_tests(PROBLEM, 2).title == (
        "Level 2 examples of bank-project-python, written by `cstudy submit`."
    )


def test_the_tests_know_the_entry_and_its_class():
    tests = level_tests(PROBLEM, 1)
    assert (tests.entry, tests.signature.name) == ("bank.bank", "Bank")


def test_a_level_the_problem_lacks_is_rejected():
    with pytest.raises(ValueError, match="bank-project-python has no level 3"):
        level_tests(PROBLEM, 3)


def test_a_problem_of_another_kind_is_rejected():
    problem = replace(PROBLEM, meta=replace(PROBLEM.meta, kind=ProblemKind.PROGRESSIVE))
    with pytest.raises(ValueError, match="bank-project-python is not a project problem"):
        level_tests(problem, 1)


def test_an_operation_missing_from_the_signature_is_rejected():
    case = ops_case("ex1", 1, ("withdraw", [1, "ivy", 5], -1))
    with pytest.raises(ValueError, match="case ex1 calls withdraw, which Bank does not declare"):
        generated(project_problem(case))


@pytest.mark.parametrize("operation", ["@advance", "@spawn", "@join", "@now"])
@pytest.mark.parametrize(
    "language",
    [
        language
        for language in (Language.TYPESCRIPT, Language.JAVA, Language.KOTLIN, Language.RUST)
        if language not in HARNESS_TEST_LANGUAGES
    ],
)
def test_a_harness_operation_is_named_as_one_the_generated_tests_do_not_express_yet(
    operation, language
):
    case = ops_case("ex1", 1, ("createAccount", [1, "ivy"], True), (operation, [], None))
    meta = project_meta(language=language, clock=ProjectClock.VIRTUAL)
    message = f"case ex1 uses {operation}, which the generated tests do not express yet"
    with pytest.raises(ValueError, match=message):
        generated(project_problem(case, meta=meta))


def test_a_harness_operation_without_the_virtual_clock_is_named_the_same_way():
    case = ops_case("ex1", 1, ("@advance", [5], None))
    meta = project_meta(language=Language.GO)
    message = "case ex1 uses @advance, which the generated tests do not express yet"
    with pytest.raises(ValueError, match=message):
        generated(project_problem(case, meta=meta))


def test_a_case_without_operations_is_rejected():
    case = Case("ex1", FunctionInput({"timestamp": 1}), visible=True, level=1)
    with pytest.raises(ValueError, match="case ex1 has no operation sequence"):
        generated(project_problem(case))


def test_a_case_with_an_output_missing_is_rejected():
    case = replace(EX2, expected=Expected([None]))
    with pytest.raises(ValueError, match="case ex2 expects 1 outputs for 2 operations"):
        generated(project_problem(case))


def test_a_level_without_visible_cases_has_no_tests():
    assert generated(project_problem(HIDDEN)) == ()


def test_tests_of_a_transfer_level_use_the_transfer_method():
    assert generated(level=2)[0].calls[0].method == TRANSFER


# the virtual clock

RECEIVE = method("receive", 1, "waitMs: int", "string")
SIZE = method("size", 1, "", "int")
LEAVE = method("leave", 1, "", "void")
INBOX = ClassSignature("Inbox", (), (RECEIVE, SIZE, LEAVE))


def clock_problem(*calls, per_method: dict[str, ComparatorType] | None = None):
    comparator = ComparatorSpec(ComparatorType.OPS, per_method=per_method or {})
    meta = project_meta(
        INBOX, comparator, Language.GO, (Level(1, "Waiting"),), clock=ProjectClock.VIRTUAL
    )
    return project_problem(ops_case("ex1", 1, *calls, class_name="Inbox"), meta=meta)


def clock_operations(*calls, per_method: dict[str, ComparatorType] | None = None):
    return generated(clock_problem(*calls, per_method=per_method))[0].operations


def test_the_tests_of_a_virtual_clock_project_know_the_clock():
    assert level_tests(clock_problem(("size", [], 0)), 1).virtual_clock


def test_the_tests_of_a_project_on_the_real_clock_do_not():
    assert not level_tests(PROBLEM, 1).virtual_clock


def test_advance_moves_the_clock_by_its_milliseconds():
    assert clock_operations(("@advance", [1500], None)) == (Advance(1500),)


def test_spawn_names_the_task_and_the_call_it_starts():
    assert clock_operations(("@spawn", ["r1", "receive", 5000], None), ("@join", ["r1"], "a"))[
        0
    ] == Spawn("r1", RECEIVE, (5000,))


def test_join_expects_the_result_of_the_call_its_task_started():
    operations = clock_operations(("@spawn", ["r1", "receive", 5000], None), ("@join", ["r1"], "a"))
    assert operations[1] == Join("r1", Call(RECEIVE, (5000,), "a", ComparatorType.EXACT))


def test_join_compares_with_the_comparator_of_the_spawned_method():
    operations = clock_operations(
        ("@spawn", ["r1", "receive", 5000], None),
        ("@join", ["r1"], "a"),
        per_method={"receive": ComparatorType.UNORDERED},
    )
    assert isinstance(operations[1], Join)
    assert operations[1].call.comparator is ComparatorType.UNORDERED


def test_join_of_a_void_method_expects_nothing():
    operations = clock_operations(("@spawn", ["l", "leave"], None), ("@join", ["l"], None))
    assert isinstance(operations[1], Join)
    assert not operations[1].call.returns_value


def test_now_expects_the_milliseconds_since_the_case_started():
    assert clock_operations(("@now", [], 1000)) == (Now(1000),)


def test_calls_and_harness_operations_keep_the_order_of_the_case():
    operations = clock_operations(
        ("@spawn", ["r1", "receive", 5000], None),
        ("@advance", [1000], None),
        ("size", [], 0),
        ("@join", ["r1"], ""),
        ("@now", [], 1000),
    )
    assert [type(operation) for operation in operations] == [Spawn, Advance, Call, Join, Now]


def test_calls_are_the_operations_of_a_test_on_the_real_clock():
    assert generated(clock_problem(("size", [], 0)))[0].calls == (
        Call(SIZE, (), 0, ComparatorType.EXACT),
    )


def test_a_test_with_harness_operations_has_no_calls_to_list():
    test = generated(clock_problem(("@advance", [5], None)))[0]
    with pytest.raises(ValueError, match="holds harness operations"):
        assert test.calls


def test_a_spawn_of_a_method_the_class_lacks_is_rejected():
    case = ("@spawn", ["r1", "withdraw", 5], None)
    with pytest.raises(ValueError, match="case ex1 calls withdraw, which Inbox does not declare"):
        clock_operations(case)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (("@advance", [], None), "case ex1: @advance takes one whole number of milliseconds"),
        (("@advance", ["1"], None), "case ex1: @advance takes one whole number of milliseconds"),
        (("@advance", [True], None), "case ex1: @advance takes one whole number of milliseconds"),
        (
            ("@spawn", ["r1"], None),
            "case ex1: @spawn takes a task name, a method and its arguments",
        ),
        (("@join", ["r1"], ""), "case ex1: @join of r1, which no @spawn started"),
        (("@join", [], ""), "case ex1: @join takes the name of one spawned task"),
        (("@now", [1], 0), "case ex1: @now takes no arguments"),
        (("@now", [], "0"), "case ex1: @now expects a whole number of milliseconds"),
        (("@now", [], True), "case ex1: @now expects a whole number of milliseconds"),
        (("@bogus", [], None), "case ex1 uses @bogus, which is not a harness operation"),
    ],
)
def test_a_malformed_harness_operation_is_rejected_with_its_reason(call, message):
    with pytest.raises(ValueError, match=message):
        clock_operations(call)


def test_a_task_joined_twice_is_rejected():
    spawned = ("@spawn", ["r1", "size"], None)
    with pytest.raises(ValueError, match="case ex1: @join of r1, which no @spawn started"):
        clock_operations(spawned, ("@join", ["r1"], 0), ("@join", ["r1"], 0))


def test_a_task_name_spawned_twice_before_its_join_is_rejected():
    spawned = ("@spawn", ["r1", "size"], None)
    with pytest.raises(ValueError, match="case ex1: @spawn of r1, which is running already"):
        clock_operations(spawned, spawned)


def test_a_task_that_is_never_joined_is_rejected():
    with pytest.raises(ValueError, match="case ex1: @spawn of r1 is never joined"):
        clock_operations(("@spawn", ["r1", "size"], None), ("@advance", [5], None))
