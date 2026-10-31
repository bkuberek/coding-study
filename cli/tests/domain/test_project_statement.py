"""A project problem's rendered statement speaks its language: method names in examples, and a
`Methods to add` line opening each level (docs/specs/problem-format.md#statement)."""

from dataclasses import replace

from coding_study.domain.cases import OperationSequence
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language
from coding_study.domain.project import in_language_names, render_project_statement
from coding_study.domain.signature import ClassSignature
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
