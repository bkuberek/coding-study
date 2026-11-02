"""`node:test` files generated from a project level's visible cases
(docs/specs/problem-format.md#generated-test-files).

The layouts below are those Prettier 3 produces with its defaults;
test_typescript_test_generator_checks.py runs Prettier, `node --test` and `tsc` on generated files
to keep the two in step.
"""

from collections.abc import Sequence
from dataclasses import replace

import pytest

from coding_study.adapters.languages.typescript.test_generator import TypeScriptTestGenerator
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language, Level
from coding_study.domain.project import Project
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature, Method, Param
from coding_study.domain.type_dsl import parse_value_type
from coding_study.domain.virtual_clock import ProjectClock
from tests.project_builders import OPS, method, ops_case, project_meta, project_problem

GENERATOR = TypeScriptTestGenerator()
SPEC_EXAMPLE = """\
// Level 1 examples of bank-project-typescript, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Bank } from "../src/bank.ts";

test("ex1", () => {
  const bank = new Bank();
  assert.equal(bank.createAccount(1, "ivy"), true);
  assert.equal(bank.createAccount(2, "leo"), true);
  assert.equal(bank.createAccount(3, "ivy"), false);
  assert.equal(bank.deposit(4, "ivy", 800), 800);
});
"""
SPEC_EX1 = ops_case(
    "ex1",
    1,
    ("createAccount", [1, "ivy"], True),
    ("createAccount", [2, "leo"], True),
    ("createAccount", [3, "ivy"], False),
    ("deposit", [4, "ivy", 800], 800),
)
DEPOSIT_CALL = ("deposit", [1, "a", 5], -1)
SIZE = method("size", 1, returns="int")
SIZE_CALL = ("size", [], 0)
"""A call that uses the instance, for tests about building it."""
HEADER_LINES = 7
"""The two header comments, the imports, a blank line between them and one after them."""
TYPESCRIPT_META = project_meta(language=Language.TYPESCRIPT)
FLOAT = ComparatorSpec(ComparatorType.OPS, per_method={"average": ComparatorType.FLOAT})


def generated(*cases, meta=TYPESCRIPT_META, level: int = 1) -> str:
    return GENERATOR.generate(level_tests(project_problem(*cases, meta=meta), level))


def typescript_meta(signature: ClassSignature, comparator: ComparatorSpec = OPS):
    return project_meta(signature=signature, comparator=comparator, language=Language.TYPESCRIPT)


def statement(
    found: Method,
    arguments: Sequence[JsonValue],
    expected: JsonValue,
    comparator: ComparatorSpec = OPS,
) -> str:
    """What the generated test makes of one call to `found`, after the constructor line."""
    meta = typescript_meta(ClassSignature("Bank", (), (found,)), comparator)
    text = generated(ops_case("ex1", 1, (found.name, arguments, expected)), meta=meta)
    return text.split("  const bank = new Bank();\n", 1)[1].removesuffix("});\n")


def lines_of(text: str) -> list[str]:
    return text.splitlines()


def test_level_1_matches_the_spec_example():
    assert generated(SPEC_EX1) == SPEC_EXAMPLE


def test_generation_is_byte_stable():
    assert generated(SPEC_EX1) == generated(SPEC_EX1)


def test_a_later_level_names_the_command_that_opens_it():
    case = ops_case("ex2", 2, ("transfer", [1, "a", "b", 5], -1))
    assert generated(case, level=2).startswith(
        "// Level 2 examples of bank-project-typescript, written by `cstudy submit`.\n"
    )


def test_each_case_is_a_test_named_after_its_id():
    assert '\ntest("big-1", () => {\n' in generated(ops_case("big-1", 1, DEPOSIT_CALL))


def test_tests_follow_one_another_after_a_blank_line():
    second = ops_case("ex2", 1, DEPOSIT_CALL)
    assert '\n});\n\ntest("ex2", () => {\n' in generated(SPEC_EX1, second)


def test_a_level_without_visible_cases_holds_only_its_header():
    assert generated() == (
        "// Level 1 examples of bank-project-typescript, written by `cstudy start`.\n"
        "// Yours to edit and extend: cstudy never rewrites this file.\n"
    )


def test_a_long_title_wraps_within_80_columns():
    slug = "a-bank-project-with-a-long-name-to-wrap-typescript"
    meta = replace(TYPESCRIPT_META, slug=slug)
    assert lines_of(generated(meta=meta))[:2] == [
        f"// Level 1 examples of {slug},",
        "// written by `cstudy start`.",
    ]


# imports


def entry_import(entry: str, tests: str) -> str:
    meta = replace(TYPESCRIPT_META, project=Project(entry, tests))
    return lines_of(generated(SPEC_EX1, meta=meta))[5]


@pytest.mark.parametrize(
    ("entry", "tests", "path"),
    [
        ("src/bank.ts", "tests", "../src/bank.ts"),
        ("src/bank.ts", "tests/levels", "../../src/bank.ts"),
        ("bank.ts", "tests", "../bank.ts"),
        ("src/bank.ts", "src", "./bank.ts"),
        ("src/core/bank.ts", "src/tests", "../core/bank.ts"),
    ],
)
def test_the_entry_file_is_imported_relative_to_the_tests(entry, tests, path):
    assert entry_import(entry, tests) == f'import {{ Bank }} from "{path}";'


def test_a_file_without_assertions_imports_only_the_test_function():
    reset = method("reset", 1, "timestamp: long")
    meta = typescript_meta(ClassSignature("Bank", (), (reset,)))
    text = generated(ops_case("ex1", 1, ("reset", [1], None)), meta=meta)
    assert lines_of(text)[2:5] == [
        'import { test } from "node:test";',
        "",
        'import { Bank } from "../src/bank.ts";',
    ]


# notes


def note_lines(note: str) -> list[str]:
    text = generated(ops_case("ex1", 1, DEPOSIT_CALL, note=note))
    return lines_of(text)[HEADER_LINES:-4]


def test_a_note_is_a_comment_above_its_test():
    assert note_lines("deposits add up") == ["// deposits add up"]


def test_a_note_is_one_line_of_text():
    assert note_lines("deposits\n   add up") == ["// deposits add up"]


def test_a_long_note_wraps_within_80_columns():
    note = (
        "booked transfers run at their due time, earliest due first, and count as money sent "
        "by their source"
    )
    assert note_lines(note) == [
        "// booked transfers run at their due time, earliest due first, and count as",
        "// money sent by their source",
    ]


# building the class


def test_the_class_takes_the_constructor_arguments():
    signature = ClassSignature("Bank", (Param("currency", parse_value_type("string")),), (SIZE,))
    meta = replace(typescript_meta(signature), levels=(Level(1, "Accounts"),))
    text = generated(ops_case("ex1", 1, SIZE_CALL, constructor=["eur"]), meta=meta)
    assert '  const bank = new Bank("eur");\n' in text


def test_a_case_with_only_the_constructor_builds_the_class_without_naming_it():
    assert generated(ops_case("ex1", 1)).endswith('test("ex1", () => {\n  new Bank();\n});\n')


@pytest.mark.parametrize(
    ("class_name", "instance"),
    [("LRUCache", "lruCache"), ("BankAccount", "bankAccount"), ("Delete", "delete_")],
)
def test_the_instance_is_the_class_in_camel_case_unless_reserved(class_name, instance):
    meta = typescript_meta(ClassSignature(class_name, (), (SIZE,)))
    text = generated(ops_case("ex1", 1, SIZE_CALL, class_name=class_name), meta=meta)
    assert f"  const {instance} = new {class_name}();\n" in text


def test_the_instance_never_hides_the_test_function():
    meta = typescript_meta(ClassSignature("Test", (), (SIZE,)))
    text = generated(ops_case("ex1", 1, SIZE_CALL, class_name="Test"), meta=meta)
    assert "  const test_ = new Test();\n" in text


# exact


def test_a_void_call_stands_alone():
    reset = method("reset", 1, "timestamp: long")
    assert statement(reset, [1], None) == "  bank.reset(1);\n"


def test_an_absent_result_is_null():
    name = method("nameOf", 1, "id: int", "string")
    assert statement(name, [1], None) == "  assert.equal(bank.nameOf(1), null);\n"


def test_a_list_result_compares_deeply():
    flags = method("flags", 1, "", "bool[]")
    assert statement(flags, [], [True, False]) == (
        "  assert.deepEqual(bank.flags(), [true, false]);\n"
    )


def test_an_empty_list_result():
    names = method("names", 1, "", "list<string>")
    assert statement(names, [], []) == "  assert.deepEqual(bank.names(), []);\n"


def test_a_negative_result():
    deposit = method("deposit", 1, "amount: long", "long")
    assert statement(deposit, [5], -1) == "  assert.equal(bank.deposit(5), -1);\n"


@pytest.mark.parametrize(
    ("value", "literal"),
    [(2.5, "2.5"), (2.0, "2"), (1e-07, "1e-7"), (1e-06, "0.000001"), (1e21, "1e21"), (-0.0, "0")],
)
def test_numbers_are_written_as_javascript_writes_them(value, literal):
    average = method("average", 1, "", "double")
    assert statement(average, [], value) == f"  assert.equal(bank.average(), {literal});\n"


@pytest.mark.parametrize(
    ("value", "literal"),
    [
        ("it's", '"it\'s"'),
        ('say "hi"', "'say \"hi\"'"),
        ("a\\b\n\x01\u2028", '"a\\\\b\\n\\x01\\u2028"'),
        ("café", '"café"'),
    ],
)
def test_strings_are_written_as_prettier_quotes_them(value, literal):
    name = method("nameOf", 1, "", "string")
    assert statement(name, [], value) == f"  assert.equal(bank.nameOf(), {literal});\n"


def test_a_date_is_its_iso_string():
    due = method("dueOn", 1, "day: date", "date")
    assert statement(due, ["2026-01-01"], "2026-02-01") == (
        '  assert.equal(bank.dueOn("2026-01-01"), "2026-02-01");\n'
    )


# unordered


def unordered(name: str) -> ComparatorSpec:
    return ComparatorSpec(ComparatorType.OPS, per_method={name: ComparatorType.UNORDERED})


def test_unordered_results_are_sorted_against_a_sorted_literal():
    top = method("top", 1, "n: int", "list<string>")
    assert statement(top, [2], ["zoe", "abe"], unordered("top")) == (
        '  assert.deepEqual([...bank.top(2)].sort(), ["abe", "zoe"]);\n'
    )


def test_unordered_numbers_sort_as_javascript_sorts_them_by_their_text():
    ids = method("ids", 1, "", "list<int>")
    assert statement(ids, [], [9, 100, 10], unordered("ids")) == (
        "  assert.deepEqual([...bank.ids()].sort(), [10, 100, 9]);\n"
    )


def test_unordered_strings_sort_by_utf16_code_units():
    names = method("names", 1, "", "list<string>")
    assert statement(names, [], ["\uff01", "\U0001f600"], unordered("names")) == (
        '  assert.deepEqual([...bank.names()].sort(), ["\U0001f600", "\uff01"]);\n'
    )


def test_unordered_lists_sort_by_their_joined_text():
    pairs = method("pairs", 1, "", "list<list<int>>")
    assert statement(pairs, [], [[2], [10, 1]], unordered("pairs")) == (
        "  assert.deepEqual([...bank.pairs()].sort(), [[10, 1], [2]]);\n"
    )


def test_an_unordered_result_that_is_not_a_list_compares_exactly():
    size = method("size", 1, "", "int")
    assert statement(size, [], 3, unordered("size")) == "  assert.equal(bank.size(), 3);\n"


# float


ASSERT_CLOSE = """\
function assertClose(actual: unknown, expected: unknown, tolerance: number) {
  if (Array.isArray(actual) && Array.isArray(expected)) {
    assert.equal(actual.length, expected.length);
    for (const [index, item] of expected.entries()) {
      assertClose(actual[index], item, tolerance);
    }
  } else if (typeof actual === "number" && typeof expected === "number") {
    const bound = tolerance * Math.max(1, Math.abs(expected));
    assert.ok(
      Math.abs(actual - expected) <= bound,
      `${actual} is not within ${bound} of ${expected}`,
    );
  } else {
    assert.deepEqual(actual, expected);
  }
}
"""


def test_float_results_compare_within_the_tolerance():
    average = method("average", 1, "", "double")
    assert statement(average, [], 2.5, FLOAT) == "  assertClose(bank.average(), 2.5, 0.000001);\n"


def test_float_comparisons_define_their_helper_once_after_the_imports():
    average = method("average", 1, "", "double")
    meta = typescript_meta(ClassSignature("Bank", (), (average,)), FLOAT)
    first, second = (ops_case(case_id, 1, ("average", [], 2.5)) for case_id in ("ex1", "ex2"))
    text = generated(first, second, meta=meta)
    assert text.split('\nimport { Bank } from "../src/bank.ts";\n\n', 1)[1].startswith(
        f'{ASSERT_CLOSE}\ntest("ex1", () => {{\n'
    )


def test_a_list_of_floats_compares_each_number_within_the_tolerance():
    average = method("average", 1, "", "double[]")
    assert statement(average, [], [1.5, 2], FLOAT) == (
        "  assertClose(bank.average(), [1.5, 2], 0.000001);\n"
    )


def test_a_float_comparison_without_numbers_stays_exact():
    average = method("average", 1, "", "bool")
    assert statement(average, [], True, FLOAT) == "  assert.equal(bank.average(), true);\n"


# layouts too long for one line


TOP = method("topSpenders", 1, "timestamp: long; n: int", "list<string>")
LONG_NAME = "account-with-a-very-very-long-name"


def test_a_long_list_result_breaks_one_item_per_line_after_the_call():
    expected: list[JsonValue] = ["nia(700)", "oz(450)", "pam(0)", "abc(1)", "def(2)", "ghi(3)"]
    assert statement(TOP, [10, 3], expected) == (
        "  assert.deepEqual(bank.topSpenders(10, 3), [\n"
        + "".join(f'    "{item}",\n' for item in expected)
        + "  ]);\n"
    )


def test_a_long_list_of_numbers_fills_its_own_line():
    history = method("history", 1, "timestamp: long; n: int", "list<long>")
    expected: list[JsonValue] = list(range(100, 1500, 100))
    assert statement(history, [10, 3], expected) == (
        "  assert.deepEqual(\n"
        "    bank.history(10, 3),\n"
        "    [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400],\n"
        "  );\n"
    )


def test_a_list_of_several_pairs_puts_each_pair_on_its_own_line():
    pairs = method("pairs", 1, "", "int[][]")
    assert statement(pairs, [], [[1, 2], [3, 4]]) == (
        "  assert.deepEqual(bank.pairs(), [\n    [1, 2],\n    [3, 4],\n  ]);\n"
    )


def test_a_long_call_breaks_its_arguments_one_per_line():
    schedule = method(
        "scheduleTransfer",
        1,
        "timestamp: long; sourceId: string; targetId: string; amount: long; delay: long",
        "string",
    )
    arguments = [1000000, "account-with-long-name", "another-long-name", 5, 1]
    assert statement(schedule, arguments, "transfer1") == (
        "  assert.equal(\n"
        "    bank.scheduleTransfer(\n"
        "      1000000,\n"
        '      "account-with-long-name",\n'
        '      "another-long-name",\n'
        "      5,\n"
        "      1,\n"
        "    ),\n"
        '    "transfer1",\n'
        "  );\n"
    )


def test_a_long_void_call_puts_each_argument_on_its_own_line():
    book = method(
        "book", 1, "timestamp: long; sourceId: string; targetId: string; amount: long; delay: long"
    )
    arguments = [1000000, LONG_NAME, "another-very-very-long-name", 5000000, 77]
    assert statement(book, arguments, None) == (
        "  bank.book(\n"
        "    1000000,\n"
        f'    "{LONG_NAME}",\n'
        '    "another-very-very-long-name",\n'
        "    5000000,\n"
        "    77,\n"
        "  );\n"
    )


def test_a_long_constructor_breaks_its_arguments():
    params = tuple(
        Param(name, parse_value_type(type_text))
        for name, type_text in (("a", "long"), ("b", "string"), ("c", "string"))
    )
    meta = typescript_meta(ClassSignature("Bank", params, (SIZE,)))
    arguments = [1000000, "account-with-a-very-long-name", "another-lon"]
    text = generated(ops_case("ex1", 1, SIZE_CALL, constructor=arguments), meta=meta)
    assert (
        "  const bank = new Bank(\n"
        "    1000000,\n"
        '    "account-with-a-very-long-name",\n'
        '    "another-lon",\n'
        "  );\n"
    ) in text


def test_a_constructor_too_long_for_its_line_moves_after_the_equals_sign():
    name = "BankAccountWithAnExtremelyLongNameThatNeedsItsOwnLine"
    case = ops_case("ex1", 1, SIZE_CALL, class_name=name)
    text = generated(case, meta=typescript_meta(ClassSignature(name, (), (SIZE,))))
    assert (
        f"  const bankAccountWithAnExtremelyLongNameThatNeedsItsOwnLine =\n    new {name}();\n"
    ) in text


# the virtual clock (docs/specs/problem-format.md#generated-tests-on-the-virtual-clock)

PUBLISH = method("publish", 1, "body: string", "int")
RECEIVE = replace(method("receive", 1, "waitMs: int", "string"), is_async=True)
LEAVE = replace(method("leave", 1, "", "void"), is_async=True)
INBOX = ClassSignature("Inbox", (), (PUBLISH, RECEIVE, LEAVE))
CLOCK_EXAMPLE = """\
// Level 1 examples of bank-project-typescript, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Inbox } from "../src/bank.ts";
import { virtualClock } from "./virtual-clock.ts";

// a waiting receive takes a message published while it waits
test("ex1", async (t) => {
  const clock = virtualClock(t);
  const inbox = new Inbox();
  await clock.settle();
  const r1 = inbox.receive(5000);
  await clock.settle();
  await clock.advance(1000);
  assert.equal(inbox.publish("a"), 1);
  await clock.settle();
  assert.equal(await clock.wait(r1), "a");
  await clock.settle();
  assert.equal(clock.now(), 1000);
  assert.equal(await clock.wait(inbox.receive(2000)), "");
  await clock.settle();
  assert.equal(clock.now(), 3000);
});
"""
CLOCK_EX1 = ops_case(
    "ex1",
    1,
    ("@spawn", ["r1", "receive", 5000], None),
    ("@advance", [1000], None),
    ("publish", ["a"], 1),
    ("@join", ["r1"], "a"),
    ("@now", [], 1000),
    ("receive", [2000], ""),
    ("@now", [], 3000),
    note="a waiting receive takes a message published while it waits",
    class_name="Inbox",
)


def clock_meta(signature: ClassSignature = INBOX, comparator: ComparatorSpec = OPS):
    return project_meta(
        signature,
        comparator,
        Language.TYPESCRIPT,
        (Level(1, "Waiting"),),
        clock=ProjectClock.VIRTUAL,
    )


def on_the_clock(*calls, meta=None, class_name: str = "Inbox") -> str:
    case = ops_case("ex1", 1, *calls, class_name=class_name)
    return generated(case, meta=meta or clock_meta())


def clock_body(text: str) -> str:
    """The lines of the one test, after its first line."""
    return text.split('test("ex1", async (t) => {\n', 1)[1].removesuffix("});\n")


def test_a_level_on_the_virtual_clock_matches_the_spec_example():
    assert generated(CLOCK_EX1, meta=clock_meta()) == CLOCK_EXAMPLE


def test_generation_on_the_virtual_clock_is_byte_stable():
    assert generated(CLOCK_EX1, meta=clock_meta()) == generated(CLOCK_EX1, meta=clock_meta())


def test_a_test_of_calls_alone_settles_between_them():
    text = on_the_clock(("publish", ["a"], 1), ("publish", ["b"], 2))
    assert clock_body(text) == (
        "  const clock = virtualClock(t);\n"
        "  const inbox = new Inbox();\n"
        "  await clock.settle();\n"
        '  assert.equal(inbox.publish("a"), 1);\n'
        "  await clock.settle();\n"
        '  assert.equal(inbox.publish("b"), 2);\n'
    )


def test_a_constructor_alone_still_runs_on_the_clock():
    assert clock_body(on_the_clock()) == "  virtualClock(t);\n  new Inbox();\n"


def test_the_helper_is_imported_from_the_starters_tests_directory():
    meta = replace(
        clock_meta(), project=Project("src/bank.ts", "tests/levels", ProjectClock.VIRTUAL)
    )
    text = on_the_clock(("publish", ["a"], 1), meta=meta)
    assert 'import { virtualClock } from "../virtual-clock.ts";\n' in text


def test_an_async_call_is_awaited_while_the_clock_moves():
    text = on_the_clock(("receive", [5], "a"))
    assert clock_body(text).endswith('  assert.equal(await clock.wait(inbox.receive(5)), "a");\n')


def test_an_async_call_that_returns_nothing_is_awaited_alone():
    text = on_the_clock(("leave", [], None))
    assert clock_body(text).endswith("  await clock.wait(inbox.leave());\n")


def test_advance_and_now_need_no_settling_after_them():
    text = on_the_clock(("@advance", [5], None), ("@now", [], 5), ("publish", ["a"], 1))
    assert clock_body(text) == (
        "  const clock = virtualClock(t);\n"
        "  const inbox = new Inbox();\n"
        "  await clock.settle();\n"
        "  await clock.advance(5);\n"
        "  assert.equal(clock.now(), 5);\n"
        '  assert.equal(inbox.publish("a"), 1);\n'
    )


def test_spawn_keeps_the_pending_promise_in_a_variable_named_after_the_task():
    text = on_the_clock(("@spawn", ["r1", "receive", 5], None), ("@join", ["r1"], ""))
    assert "  const r1 = inbox.receive(5);\n  await clock.settle();\n" in text


def test_join_waits_for_the_promise_and_checks_its_result():
    text = on_the_clock(("@spawn", ["r1", "receive", 5], None), ("@join", ["r1"], "x"))
    assert clock_body(text).endswith('  assert.equal(await clock.wait(r1), "x");\n')


def test_join_of_a_task_that_returns_nothing_only_waits():
    text = on_the_clock(("@spawn", ["l", "leave"], None), ("@join", ["l"], None))
    assert clock_body(text).endswith("  await clock.wait(l);\n")


def test_join_sorts_an_unordered_result_first():
    names = replace(method("names", 1, "", "list<string>"), is_async=True)
    comparator = ComparatorSpec(ComparatorType.OPS, per_method={"names": ComparatorType.UNORDERED})
    meta = clock_meta(ClassSignature("Inbox", (), (names,)), comparator)
    text = on_the_clock(("@spawn", ["n", "names"], None), ("@join", ["n"], ["b", "a"]), meta=meta)
    assert clock_body(text).endswith(
        '  assert.deepEqual([...(await clock.wait(n))].sort(), ["a", "b"]);\n'
    )


def test_join_of_a_float_result_allows_the_tolerance():
    ratio = replace(method("ratio", 1, "", "double"), is_async=True)
    comparator = ComparatorSpec(ComparatorType.OPS, per_method={"ratio": ComparatorType.FLOAT})
    meta = clock_meta(ClassSignature("Inbox", (), (ratio,)), comparator)
    text = on_the_clock(("@spawn", ["x", "ratio"], None), ("@join", ["x"], 0.5), meta=meta)
    assert clock_body(text).endswith("  assertClose(await clock.wait(x), 0.5, 0.000001);\n")


def test_a_task_name_becomes_a_typescript_identifier():
    text = on_the_clock(
        ("@spawn", ["consumer-1", "receive", 5], None), ("@join", ["consumer-1"], "")
    )
    assert "  const consumer1 = inbox.receive(5);\n" in text
    assert '  assert.equal(await clock.wait(consumer1), "");\n' in text


def test_a_task_name_with_words_becomes_camel_case():
    text = on_the_clock(
        ("@spawn", ["slow-reader", "receive", 5], None), ("@join", ["slow-reader"], "")
    )
    assert "  const slowReader = inbox.receive(5);\n" in text


def test_a_task_never_takes_a_name_the_test_uses():
    text = on_the_clock(
        ("@spawn", ["clock", "receive", 5], None),
        ("@join", ["clock"], ""),
        ("@spawn", ["inbox", "receive", 5], None),
        ("@join", ["inbox"], ""),
    )
    assert "  const task1 = inbox.receive(5);\n" in text
    assert "  const task2 = inbox.receive(5);\n" in text


def test_the_instance_never_takes_the_clocks_name():
    signature = ClassSignature("Clock", (), (PUBLISH,))
    text = on_the_clock(("publish", ["a"], 1), meta=clock_meta(signature), class_name="Clock")
    assert "  const clock_ = new Clock();\n" in text


def test_the_real_clock_keeps_plain_tests():
    meta = project_meta(INBOX, language=Language.TYPESCRIPT)
    text = generated(ops_case("ex1", 1, ("publish", ["a"], 1), class_name="Inbox"), meta=meta)
    assert 'test("ex1", () => {\n  const inbox = new Inbox();\n' in text
