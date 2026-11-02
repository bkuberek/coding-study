"""A project problem's rendered statement speaks its language: method names in examples, and a
`Methods to add` line opening each level (docs/specs/problem-format.md#statement)."""

from dataclasses import replace

import pytest

from coding_study.domain.cases import OperationSequence
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language, Level
from coding_study.domain.project import in_language_names, render_project_statement
from coding_study.domain.signature import ClassSignature, Param
from coding_study.domain.type_dsl import Scalar, ScalarType
from coding_study.domain.virtual_clock import ProjectClock
from tests.project_builders import BANK, method, ops_case, project_meta, project_problem

EX1 = ops_case("ex1", 1, ("createAccount", [1, "ivy"], True), ("deposit", [2, "ivy", 800], 800))
EX2 = ops_case("ex2", 2, ("transfer", [3, "ivy", "leo", 200], -1))
PROBLEM = project_problem(EX1, EX2)
PROBLEM_MD = """\
# Bank Project

## Statement

Build a bank.

## Project

Keep `Bank` in `bank/bank.py`.

## Level 1: Accounts

- `create_account(timestamp, account_id)`: opens an account.

### Example 1

<!-- case: ex1 -->

## Level 2: Transfers
- `transfer(timestamp, source_id, target_id, amount)`: moves money.

### Example 1

<!-- case: ex2 -->

## Constraints

- small
"""
LEVEL_1_METHODS = (
    "Methods to add: create_account(timestamp: int, account_id: str) -> bool, "
    "deposit(timestamp: int, account_id: str, amount: int) -> int"
)
LEVEL_2_METHODS = (
    "Methods to add: transfer(timestamp: int, source_id: str, target_id: str, amount: int) -> int"
)


def rendered(unlocked: int = 2, problem=PROBLEM, markdown: str | None = PROBLEM_MD) -> str:
    return render_project_statement(problem, markdown, unlocked)


def lines_after(heading: str, text: str, count: int = 3) -> list[str]:
    lines = text.splitlines()
    start = lines.index(heading)
    return lines[start + 1 : start + 1 + count]


def test_each_level_opens_with_the_methods_it_adds():
    assert lines_after("## Level 1: Accounts", rendered()) == ["", LEVEL_1_METHODS, ""]


def test_the_methods_line_is_set_apart_from_text_right_under_the_heading():
    assert lines_after("## Level 2: Transfers", rendered()) == ["", LEVEL_2_METHODS, ""]


def test_a_locked_level_shows_no_methods():
    assert "transfer(" not in rendered(unlocked=1)


def test_a_level_that_adds_no_methods_has_no_methods_line():
    signature = ClassSignature("Bank", (), BANK.methods[:2])
    problem = project_problem(EX1, EX2, meta=project_meta(signature=signature))
    assert lines_after("## Level 2: Transfers", rendered(problem=problem), 1) == [
        "- `transfer(timestamp, source_id, target_id, amount)`: moves money."
    ]


def test_example_operations_use_the_language_method_names():
    assert 'Operations: ["Bank", "create_account", "deposit"]' in rendered()


def test_typescript_keeps_the_canonical_names():
    problem = project_problem(EX1, EX2, meta=project_meta(language=Language.TYPESCRIPT))
    assert 'Operations: ["Bank", "createAccount", "deposit"]' in rendered(problem=problem)


def test_typescript_methods_read_as_typescript_declares_them():
    problem = project_problem(EX1, EX2, meta=project_meta(language=Language.TYPESCRIPT))
    assert "Methods to add: transfer(timestamp: number, sourceId: string" in rendered(
        problem=problem
    )


def test_an_async_python_method_reads_as_python_declares_it():
    waits = replace(method("waitFor", 1, "key: string; waitMs: long", "string"), is_async=True)
    signature = ClassSignature("Bank", (), (method("put", 1, "key: string", "string"), waits))
    meta = replace(project_meta(signature=signature, levels=(Level(1, "Waits"),)))
    problem = project_problem(meta=meta)
    markdown = "# Bank\n\n## Level 1: Waits\n"
    assert lines_after("## Level 1: Waits", rendered(1, problem, markdown), 2) == [
        "",
        "Methods to add: put(key: str) -> str, async def wait_for(key: str, wait_ms: int) -> str",
    ]


def test_an_async_typescript_method_returns_a_promise():
    waits = replace(method("waitFor", 1, "key: string; waitMs: long", "string"), is_async=True)
    signature = ClassSignature("Bank", (), (waits,))
    meta = project_meta(signature=signature, language=Language.TYPESCRIPT, levels=(Level(1, "W"),))
    markdown = "# Bank\n\n## Level 1: W\n"
    assert lines_after("## Level 1: W", rendered(1, project_problem(meta=meta), markdown), 2) == [
        "",
        "Methods to add: waitFor(key: string, waitMs: number): Promise<string>",
    ]


def test_expected_outputs_keep_their_method_types():
    balance_on = method("balanceOn", 1, "day: date", "decimal")
    signature = ClassSignature("Bank", (), (balance_on,))
    case = ops_case("ex1", 1, ("balanceOn", ["2026-01-01"], "2.50"))
    problem = project_problem(case, meta=project_meta(signature=signature))
    markdown = "# Bank\n\n## Level 1: Accounts\n\n<!-- case: ex1 -->\n"
    assert "Output:     [null, 2.50]" in rendered(1, problem, markdown)


def test_without_problem_md_the_statement_still_renders():
    assert "create_account" in rendered(markdown=None)


def test_a_methods_line_is_never_added_inside_a_code_fence():
    markdown = PROBLEM_MD.replace("Build a bank.", "```md\n## Level 1: Accounts\n```")
    assert rendered(markdown=markdown).count(LEVEL_1_METHODS) == 1


# the problem in its language's names


def test_operations_are_renamed_but_the_constructor_keeps_the_class_name():
    named = in_language_names(PROBLEM).cases[0].input
    assert isinstance(named, OperationSequence)
    assert named.ops == ("Bank", "create_account", "deposit")


CLOCK_CASE = ops_case(
    "ex3",
    2,
    ("@spawn", ["t1", "createAccount", 1, "ivy"], None),
    ("@advance", [1000], None),
    ("@join", ["t1"], True),
    ("@now", [], 1000),
)


def named_clock_case(language: Language) -> OperationSequence:
    problem = project_problem(CLOCK_CASE, meta=project_meta(language=language))
    named = in_language_names(problem).cases[0].input
    assert isinstance(named, OperationSequence)
    return named


def test_harness_operations_keep_their_names():
    assert named_clock_case(Language.GO).ops == ("Bank", "@spawn", "@advance", "@join", "@now")


@pytest.mark.parametrize(
    ("language", "method_name"),
    [
        (Language.PYTHON, "create_account"),
        (Language.RUST, "create_account"),
        (Language.TYPESCRIPT, "createAccount"),
        (Language.KOTLIN, "createAccount"),
        (Language.GO, "CreateAccount"),
    ],
)
def test_a_spawn_names_its_method_as_the_language_does(language, method_name):
    assert named_clock_case(language).args[1] == ("t1", method_name, 1, "ivy")


def test_the_other_harness_arguments_are_left_alone():
    assert named_clock_case(Language.PYTHON).args[2:] == ((1000,), ("t1",), ())


def test_a_malformed_spawn_is_left_for_the_checks_to_report():
    case = ops_case("ex3", 2, ("@spawn", ["t1"], None))
    named = in_language_names(project_problem(case)).cases[0].input
    assert isinstance(named, OperationSequence)
    assert named.args[1] == ("t1",)


def test_methods_and_parameters_are_renamed():
    signature = in_language_names(PROBLEM).meta.signature
    assert isinstance(signature, ClassSignature)
    assert [param.name for param in signature.methods[0].params] == ["timestamp", "account_id"]


def test_per_method_comparators_follow_their_methods():
    comparator = ComparatorSpec(
        ComparatorType.OPS, per_method={"createAccount": ComparatorType.EXACT}
    )
    problem = replace(PROBLEM, meta=project_meta(comparator=comparator))
    assert in_language_names(problem).meta.comparator.per_method == {
        "create_account": ComparatorType.EXACT
    }


def test_the_locked_notice_names_cstudy_submit():
    assert (
        "> Level 2 is locked. Pass every case up to level 1 with `cstudy submit` to unlock it."
        in rendered(unlocked=1)
    )


# the virtual clock, in words

PUBLISH = method("publish", 1, "body: string", "long")
RECEIVE = method("receive", 1, "waitMs: long", "string")
LEAVE = method("leave", 1, "", "void")
PRICE = method("price", 1, "on: date; amount: decimal", "decimal")
INBOX = ClassSignature(
    "Inbox", (Param("visibilityMs", ScalarType(Scalar.LONG)),), (PUBLISH, RECEIVE, LEAVE, PRICE)
)
SPOKEN_CASE = ops_case(
    "ex3",
    1,
    ("@spawn", ["r1", "receive", 5000], None),
    ("@advance", [1000], None),
    ("publish", ["a"], 1),
    ("@join", ["r1"], "a"),
    ("@now", [], 1000),
    ("receive", [2000], ""),
    ("@now", [], 3000),
    constructor=[30000],
    class_name="Inbox",
)
SPOKEN = """\
```text
Operations:
  0  Inbox(30000)
  1  r1 = Receive(5000) starts
  2  1000 ms pass
  3  Publish("a") returns 1
  4  r1 returns "a"
  5  the clock reads 1000 ms
  6  Receive(2000) returns ""
  7  the clock reads 3000 ms
```
"""
CLOCK_MD = """\
# Inbox

## Statement

Hand messages to receivers.

## Project

Keep `Inbox` in `inbox.go`.

## Level 1: Waiting

### Example 1

<!-- case: ex3 -->
"""
CLOCK_LINE = (
    "The project runs on a virtual clock: time moves only while every task waits, so a wait of "
    "any length takes no real time. A wait that nothing can end is a deadlock, which "
    "`cstudy submit` reports as `STALLED`. In the examples, `N ms pass` moves the clock and "
    "`the clock reads N ms` reads it."
)


def clock_meta(clock: ProjectClock | None = ProjectClock.VIRTUAL):
    return project_meta(INBOX, language=Language.GO, levels=(Level(1, "Waiting"),), clock=clock)


def clock_rendered(*cases, clock: ProjectClock | None = ProjectClock.VIRTUAL, markdown=CLOCK_MD):
    problem = project_problem(*cases, meta=clock_meta(clock))
    return render_project_statement(problem, markdown, 1)


def test_harness_operations_are_spoken_in_the_languages_names():
    assert SPOKEN in clock_rendered(SPOKEN_CASE)


def test_a_void_call_and_its_join_name_no_result():
    case = ops_case(
        "ex3",
        1,
        ("@spawn", ["l", "leave"], None),
        ("leave", [], None),
        ("@join", ["l"], None),
        constructor=[5],
        class_name="Inbox",
    )
    spoken = clock_rendered(case)
    assert "  1  l = Leave() starts\n  2  Leave()\n  3  l finishes\n" in spoken


def test_decimals_and_dates_are_spoken_unquoted():
    case = ops_case(
        "ex3",
        1,
        ("@spawn", ["p", "price", "2026-01-01", "2500.50"], None),
        ("@join", ["p"], "10.25"),
        constructor=[5],
        class_name="Inbox",
    )
    spoken = clock_rendered(case)
    assert "  1  p = Price(2026-01-01, 2500.50) starts\n  2  p returns 10.25\n" in spoken


def test_steps_are_numbered_as_the_reports_number_the_operations():
    steps = [("@advance", [1], None)] * 10
    case = ops_case("ex3", 1, *steps, constructor=[5], class_name="Inbox")
    spoken = clock_rendered(case)
    assert "\n   0  Inbox(5)\n   1  1 ms pass\n" in spoken
    assert "\n  10  1 ms pass\n" in spoken


def test_a_case_without_harness_operations_keeps_the_operations_arguments_and_output_lines():
    case = ops_case("ex3", 1, ("publish", ["a"], 1), constructor=[30000], class_name="Inbox")
    spoken = clock_rendered(case)
    assert 'Operations: ["Inbox", "Publish"]' in spoken
    assert "\n  0  Inbox(30000)" not in spoken


def test_the_project_section_names_the_virtual_clock():
    lines = clock_rendered(SPOKEN_CASE).splitlines()
    start = lines.index("## Project")
    assert lines[start + 1 : start + 5] == ["", CLOCK_LINE, "", "Keep `Inbox` in `inbox.go`."]


def test_a_project_on_the_real_clock_says_nothing_of_a_clock():
    case = ops_case("ex3", 1, ("publish", ["a"], 1), constructor=[30000], class_name="Inbox")
    assert "virtual clock" not in clock_rendered(case, clock=None)


def test_the_clock_line_is_not_added_when_the_statement_has_no_project_section():
    markdown = CLOCK_MD.replace("## Project\n\nKeep `Inbox` in `inbox.go`.\n\n", "")
    assert "virtual clock" not in clock_rendered(SPOKEN_CASE, markdown=markdown)
