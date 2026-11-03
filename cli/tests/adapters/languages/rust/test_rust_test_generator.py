"""libtest files generated from a project level's visible cases
(docs/specs/problem-format.md#rust-projects).

The layouts below are those rustfmt produces with its defaults;
test_rust_test_generator_checks.py runs rustfmt, clippy and the tests themselves on generated
files to keep the two in step.
"""

from collections.abc import Sequence
from dataclasses import replace

import pytest

from coding_study.adapters.languages.rust.test_generator import RustTestGenerator
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature, Method
from coding_study.domain.virtual_clock import ProjectClock
from tests.project_builders import OPS, method, ops_case, project_meta, project_problem

GENERATOR = RustTestGenerator()
SPEC_EXAMPLE = """\
//! Level 1 examples of bank-project-rust, written by `cstudy start`.
//!
//! Yours to edit and extend: cstudy never rewrites this file.

use bank::Bank;

#[test]
fn ex1() {
    let mut bank = Bank::new();
    assert!(bank.create_account(1, "ivy".to_string()));
    assert!(bank.create_account(2, "leo".to_string()));
    assert!(!bank.create_account(3, "ivy".to_string()));
    assert_eq!(bank.deposit(4, "ivy".to_string(), 800), 800);
    assert_eq!(bank.deposit(5, "max".to_string(), 50), -1);
}
"""
SPEC_EX1 = ops_case(
    "ex1",
    1,
    ("createAccount", [1, "ivy"], True),
    ("createAccount", [2, "leo"], True),
    ("createAccount", [3, "ivy"], False),
    ("deposit", [4, "ivy", 800], 800),
    ("deposit", [5, "max", 50], -1),
)
RUST_META = project_meta(language=Language.RUST)
SIZE = method("size", 1, returns="int")
SIZE_CALL = ("size", [], 0)
CONSTRUCTED = "    let mut bank = Bank::new();\n"


def generated(*cases, meta=RUST_META, level: int = 1) -> str:
    return GENERATOR.generate(level_tests(project_problem(*cases, meta=meta), level))


def rust_meta(signature: ClassSignature, comparator: ComparatorSpec = OPS):
    return project_meta(signature=signature, comparator=comparator, language=Language.RUST)


def statement(
    found: Method,
    arguments: Sequence[JsonValue],
    expected: JsonValue,
    comparator: ComparatorSpec = OPS,
) -> str:
    """What the generated test makes of one call to `found`, after the constructor line."""
    meta = rust_meta(ClassSignature("Bank", (), (found,)), comparator)
    text = generated(ops_case("ex1", 1, (found.name, arguments, expected)), meta=meta)
    return text.split(CONSTRUCTED, 1)[1].removesuffix("}\n")


def body_of(text: str) -> str:
    """The file from the first test on."""
    return text[text.index("#[test]") :]


# the file


def test_level_1_matches_the_spec_example():
    assert generated(SPEC_EX1) == SPEC_EXAMPLE


def test_generation_is_byte_stable():
    assert generated(SPEC_EX1) == generated(SPEC_EX1)


def test_a_later_level_names_the_command_that_opens_it():
    text = generated(ops_case("ex2", 2, ("transfer", [1, "a", "b", 5], -1)), level=2)
    assert text.startswith("//! Level 2 examples of bank-project-rust, written by `cstudy submit`.")


def test_tests_follow_one_another_after_a_blank_line():
    text = generated(ops_case("ex1", 1, ("deposit", [1, "a", 5], -1)), ops_case("ex2", 1))
    assert "}\n\n#[test]\nfn ex2() {\n" in text


def test_a_level_without_visible_cases_holds_only_its_header():
    text = generated(ops_case("h1", 1, ("deposit", [1, "a", 5], -1), visible=False))
    assert text == (
        "//! Level 1 examples of bank-project-rust, written by `cstudy start`.\n//!\n"
        "//! Yours to edit and extend: cstudy never rewrites this file.\n"
    )


def test_the_entry_class_is_used_from_the_crate():
    assert "\nuse bank::Bank;\n" in generated(SPEC_EX1)


# test names and notes


@pytest.mark.parametrize(
    ("case_id", "name"),
    [
        ("ex1", "ex1"),
        ("edge-empty", "edge_empty"),
        ("1-first", "case_1_first"),
        ("loop", "case_loop"),
    ],
    ids=["plain", "dashes", "digit first", "keyword"],
)
def test_each_case_is_a_test_named_after_its_id(case_id, name):
    assert f"#[test]\nfn {name}() {{\n" in generated(
        ops_case(case_id, 1, ("deposit", [1, "a", 5], -1))
    )


def test_a_note_is_a_doc_comment_above_its_test():
    text = generated(ops_case("ex1", 1, ("deposit", [1, "a", 5], -1), note="no account   yet"))
    assert "/// No account yet.\n#[test]\nfn ex1() {\n" in text


# the instance


def test_the_class_takes_the_constructor_arguments():
    signature = ClassSignature("Bank", (method("seed", 1, "seed: int").params[0],), (SIZE,))
    text = generated(ops_case("ex1", 1, SIZE_CALL, constructor=[7]), meta=rust_meta(signature))
    assert "    let mut bank = Bank::new(7);\n" in text


def test_a_case_with_only_the_constructor_builds_the_class_without_naming_it():
    assert "fn ex1() {\n    Bank::new();\n}\n" in generated(ops_case("ex1", 1))


@pytest.mark.parametrize(
    ("class_name", "instance"),
    [("LRUCache", "lru_cache"), ("Type", "type_"), ("Sorted", "sorted_")],
)
def test_the_instance_is_the_class_in_snake_case_unless_reserved(class_name, instance):
    signature = ClassSignature(class_name, (), (SIZE,))
    case = ops_case("ex1", 1, SIZE_CALL, class_name=class_name)
    text = generated(case, meta=rust_meta(signature))
    assert f"    let mut {instance} = {class_name}::new();\n" in text


# statements and values


def test_a_void_call_stands_alone():
    reset = method("reset", 1, "timestamp: long")
    assert statement(reset, [5], None) == "    bank.reset(5);\n"


def test_a_true_result_is_asserted():
    assert statement(method("ok", 1, returns="bool"), [], True) == "    assert!(bank.ok());\n"


def test_a_false_result_is_asserted_negated():
    assert statement(method("ok", 1, returns="bool"), [], False) == "    assert!(!bank.ok());\n"


def test_any_other_result_is_compared_for_equality():
    assert statement(SIZE, [], 3) == "    assert_eq!(bank.size(), 3);\n"


def test_a_string_argument_is_owned_and_an_expected_string_a_literal():
    name = method("name", 1, "id: string", "string")
    assert (
        statement(name, ["ivy"], "Ivy") == '    assert_eq!(bank.name("ivy".to_string()), "Ivy");\n'
    )


def test_a_list_argument_is_a_vec_of_its_items():
    total = method("total", 1, "amounts: long[]", "long")
    assert statement(total, [[1, 2]], 3) == "    assert_eq!(bank.total(vec![1, 2]), 3);\n"


def test_an_empty_list_argument_takes_its_type_from_the_parameter():
    total = method("total", 1, "names: list<string>", "long")
    assert statement(total, [[]], 0) == "    assert_eq!(bank.total(vec![]), 0);\n"


def test_an_empty_expected_list_spells_its_type():
    names = method("names", 1, returns="list<string>")
    assert statement(names, [], []) == "    assert_eq!(bank.names(), Vec::<String>::new());\n"


def test_an_expected_list_of_strings_is_a_vec_of_literals():
    names = method("names", 1, returns="list<string>")
    assert statement(names, [], ["a", "b"]) == '    assert_eq!(bank.names(), vec!["a", "b"]);\n'


@pytest.mark.parametrize(
    ("value", "literal"),
    [(2, "2.0"), (2.5, "2.5"), (-0.25, "-0.25"), (1e-05, "1e-05"), (1e20, "1e+20")],
)
def test_a_double_has_a_point_or_an_exponent(value, literal):
    ratio = method("ratio", 1, returns="double")
    assert statement(ratio, [], value) == f"    assert_eq!(bank.ratio(), {literal});\n"


@pytest.mark.parametrize(
    ("value", "literal"),
    [("a", "'a'"), ("'", "'\\''"), ("\\", "'\\\\'"), ("\n", "'\\n'"), ("\u0001", "'\\u{1}'")],
)
def test_a_char_is_a_rust_char_literal(value, literal):
    first = method("first", 1, returns="char")
    assert statement(first, [], value) == f"    assert_eq!(bank.first(), {literal});\n"


@pytest.mark.parametrize(
    ("value", "literal"), [('say "hi"', '"say \\"hi\\""'), ("a\tb", '"a\\tb"'), ("ünï", '"ünï"')]
)
def test_a_string_is_a_rust_string_literal(value, literal):
    name = method("name", 1, returns="string")
    assert statement(name, [], value) == f"    assert_eq!(bank.name(), {literal});\n"


def test_a_decimal_is_parsed_exactly_and_imported():
    balance = method("balance", 1, returns="decimal")
    text = generated(
        ops_case("ex1", 1, ("balance", [], "2500.50")),
        meta=rust_meta(ClassSignature("Bank", (), (balance,))),
    )
    assert "use bank::Bank;\nuse rust_decimal::Decimal;\n" in text
    assert 'assert_eq!(bank.balance(), Decimal::from_str_exact("2500.50").unwrap());' in text


def test_a_date_is_built_from_its_parts_and_imported():
    opened = method("opened", 1, returns="date")
    text = generated(
        ops_case("ex1", 1, ("opened", [], "2026-01-31")),
        meta=rust_meta(ClassSignature("Bank", (), (opened,))),
    )
    assert "use bank::Bank;\nuse chrono::NaiveDate;\n" in text
    assert "assert_eq!(bank.opened(), NaiveDate::from_ymd_opt(2026, 1, 31).unwrap());" in text


# comparators

UNORDERED = ComparatorSpec(ComparatorType.OPS, per_method={"top": ComparatorType.UNORDERED})
FLOAT = ComparatorSpec(ComparatorType.OPS, per_method={"average": ComparatorType.FLOAT})


def test_an_unordered_result_is_sorted_against_a_sorted_list():
    top = method("top", 1, returns="list<string>")
    assert statement(top, [], ["leo", "ivy"], UNORDERED) == (
        '    assert_eq!(sorted(bank.top()), vec!["ivy", "leo"]);\n'
    )


def test_unordered_decimals_sort_by_value():
    top = method("top", 1, returns="list<decimal>")
    text = statement(top, [], ["10", "9.5"], UNORDERED)
    assert text.index('"9.5"') < text.index('"10"')


def test_the_sorting_helper_is_defined_once_after_the_imports():
    top = method("top", 1, returns="int[]")
    meta = rust_meta(ClassSignature("Bank", (), (top,)), UNORDERED)
    text = generated(
        ops_case("ex1", 1, ("top", [], [2, 1])), ops_case("ex2", 1, ("top", [], [3])), meta=meta
    )
    assert text.count("fn sorted<T: Ord>") == 1
    assert "use bank::Bank;\n\nfn sorted<T: Ord>(mut items: Vec<T>) -> Vec<T> {" in text


def test_an_unordered_list_of_doubles_cannot_be_generated():
    top = method("top", 1, returns="double[]")
    with pytest.raises(ValueError, match="doubles have no order in Rust"):
        statement(top, [], [1.5], UNORDERED)


def test_a_float_result_is_close_within_the_tolerance():
    average = method("average", 1, returns="double")
    assert statement(average, [], 2.5, FLOAT) == "    assert_close(bank.average(), 2.5, 1e-06);\n"


def test_a_list_of_floats_is_close_item_by_item():
    average = method("average", 1, returns="list<double>")
    assert statement(average, [], [2.5, 3], FLOAT) == (
        "    assert_all_close(bank.average(), vec![2.5, 3.0], 1e-06);\n"
    )


def test_the_list_helper_brings_the_scalar_helper_along():
    average = method("average", 1, returns="list<double>")
    meta = rust_meta(ClassSignature("Bank", (), (average,)), FLOAT)
    text = generated(ops_case("ex1", 1, ("average", [], [2.5])), meta=meta)
    assert text.index("fn assert_close(") < text.index("fn assert_all_close(")


def test_floats_in_deeper_lists_cannot_be_generated():
    average = method("average", 1, returns="list<list<double>>")
    with pytest.raises(ValueError, match="only in double, double"):
        statement(average, [], [[2.5]], FLOAT)


def test_a_float_comparator_on_integers_compares_exactly():
    average = method("average", 1, returns="int")
    assert statement(average, [], 2, FLOAT) == "    assert_eq!(bank.average(), 2);\n"


# layouts rustfmt chooses


def test_a_long_assertion_breaks_its_arguments_one_per_line_without_a_trailing_comma():
    transfer = method("transfer", 1, "a: string; b: string; amount: long", "long")
    assert statement(transfer, ["acct-1", "acct-2", 500], 5) == (
        "    assert_eq!(\n"
        '        bank.transfer("acct-1".to_string(), "acct-2".to_string(), 500),\n'
        "        5\n"
        "    );\n"
    )


def test_arguments_wider_than_60_columns_break_even_when_the_line_fits():
    transfer = method("scheduleTransfer", 1, "a: string; b: string; amount: long", "long")
    assert statement(transfer, ["account-number-1", "account-number-2", 500], 5) == (
        "    assert_eq!(\n"
        "        bank.schedule_transfer(\n"
        '            "account-number-1".to_string(),\n'
        '            "account-number-2".to_string(),\n'
        "            500\n"
        "        ),\n"
        "        5\n"
        "    );\n"
    )


def test_a_long_call_breaks_its_arguments_one_per_line_with_a_trailing_comma():
    merge = method("mergeAccounts", 1, "timestamp: long; a: string; b: string", "void")
    assert statement(merge, [11, "a" * 25, "b" * 25], None) == (
        "    bank.merge_accounts(\n"
        "        11,\n"
        f'        "{"a" * 25}".to_string(),\n'
        f'        "{"b" * 25}".to_string(),\n'
        "    );\n"
    )


def test_a_negated_assertion_overflows_its_call():
    create = method("createAccount", 1, "timestamp: long; accountId: string", "bool")
    assert statement(create, [1, "x" * 48], False) == (
        "    assert!(!bank.create_account(\n"
        "        1,\n"
        f'        "{"x" * 48}".to_string()\n'
        "    ));\n"
    )


def test_a_long_list_of_short_numbers_fills_its_lines():
    numbers = method("numbers", 1, returns="int[]")
    assert statement(numbers, [], list(range(1, 31))) == (
        "    assert_eq!(\n"
        "        bank.numbers(),\n"
        "        vec![\n"
        "            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, "
        "17, 18, 19, 20, 21, 22, 23, 24,\n"
        "            25, 26, 27, 28, 29, 30\n"
        "        ]\n"
        "    );\n"
    )


def test_a_list_argument_overflows_its_call():
    add = method("add", 1, "names: list<string>")
    assert statement(add, [["ivy", "leo", "max", "kim"]], None) == (
        "    bank.add(vec![\n"
        '        "ivy".to_string(),\n'
        '        "leo".to_string(),\n'
        '        "max".to_string(),\n'
        '        "kim".to_string(),\n'
        "    ]);\n"
    )


# the virtual clock (docs/specs/problem-format.md#generated-tests-on-the-virtual-clock)

PUBLISH = method("publish", 1, "body: string", "int")
RECEIVE = replace(method("receive", 1, "waitMs: long", "string"), is_async=True)
LEAVE = replace(method("leave", 1, "", "void"), is_async=True)
INBOX = ClassSignature("Inbox", (), (PUBLISH, RECEIVE, LEAVE))
RUST_CLOCK_EXAMPLE = """\
//! Level 1 examples of bank-project-rust, written by `cstudy start`.
//!
//! Yours to edit and extend: cstudy never rewrites this file.

use std::sync::Arc;
use std::time::Duration;

use bank::Inbox;
use tokio::time::Instant;

/// Lets every task run until each one waits, without moving the clock. The runtime parks when
/// no task can run, and a blocking task, while it runs, keeps the paused clock still.
async fn settle() {
    let metrics = tokio::runtime::Handle::current().metrics();
    let parked = metrics.worker_park_count(0);
    tokio::task::spawn_blocking(move || {
        while metrics.worker_park_count(0) == parked {
            std::thread::yield_now();
        }
    })
    .await
    .unwrap();
}

/// Moves the clock `ms` milliseconds: each timer due on the way fires at its own time.
async fn advance(ms: u64) {
    tokio::time::sleep(Duration::from_millis(ms)).await;
    settle().await;
}

/// A waiting receive takes a message published while it waits.
#[tokio::test(start_paused = true)]
async fn ex1() {
    let start = Instant::now();
    let inbox = Arc::new(Inbox::new());
    settle().await;
    let r1 = tokio::spawn({
        let inbox = Arc::clone(&inbox);
        async move { inbox.receive(5000).await }
    });
    settle().await;
    advance(1000).await;
    assert_eq!(inbox.publish("a".to_string()), 1);
    settle().await;
    assert_eq!(r1.await.unwrap(), "a");
    settle().await;
    assert_eq!(start.elapsed().as_millis(), 1000);
    assert_eq!(inbox.receive(2000).await, "");
    settle().await;
    assert_eq!(start.elapsed().as_millis(), 3000);
}
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
CLOCK_META = project_meta(INBOX, OPS, Language.RUST, clock=ProjectClock.VIRTUAL)


def on_the_clock(*calls, meta=CLOCK_META) -> str:
    return generated(ops_case("ex1", 1, *calls, class_name="Inbox"), meta=meta)


def clock_body(text: str) -> str:
    """The lines inside the one test."""
    return text.split("async fn ex1() {\n", 1)[1].removesuffix("}\n")


def test_a_rust_level_on_the_virtual_clock_matches_the_spec_example():
    assert generated(CLOCK_EX1, meta=CLOCK_META) == RUST_CLOCK_EXAMPLE


def test_generation_on_the_virtual_clock_is_byte_stable():
    assert generated(CLOCK_EX1, meta=CLOCK_META) == generated(CLOCK_EX1, meta=CLOCK_META)


def test_a_test_settles_between_calls_but_not_after_the_last():
    text = on_the_clock(("publish", ["a"], 1), ("publish", ["b"], 2))
    assert clock_body(text) == (
        "    let mut inbox = Inbox::new();\n"
        "    settle().await;\n"
        '    assert_eq!(inbox.publish("a".to_string()), 1);\n'
        "    settle().await;\n"
        '    assert_eq!(inbox.publish("b".to_string()), 2);\n'
    )


def test_a_test_of_the_constructor_alone_needs_no_helper():
    text = on_the_clock()
    assert (clock_body(text), "async fn settle" in text) == ("    Inbox::new();\n", False)


def test_an_async_call_is_awaited():
    assert clock_body(on_the_clock(("receive", [5], "a"))).endswith(
        '    assert_eq!(inbox.receive(5).await, "a");\n'
    )


def test_an_async_void_call_is_awaited_alone():
    assert clock_body(on_the_clock(("leave", [], None))).endswith("    inbox.leave().await;\n")


def test_a_level_that_shares_the_instance_binds_it_without_mut():
    spawning = ops_case(
        "ex2", 1, ("@spawn", ["r1", "receive", 5], None), ("@join", ["r1"], ""), class_name="Inbox"
    )
    calling = ops_case("ex1", 1, ("publish", ["a"], 1), class_name="Inbox")
    text = generated(calling, spawning, meta=CLOCK_META)
    assert "    let inbox = Inbox::new();\n" in text
    assert "    let inbox = Arc::new(Inbox::new());\n" in text


def test_a_spawned_task_is_named_after_its_task_and_joined_by_that_name():
    text = on_the_clock(
        ("@spawn", ["slow-reader", "receive", 5], None), ("@join", ["slow-reader"], "")
    )
    assert "    let slow_reader = tokio::spawn({\n" in text
    assert '    assert_eq!(slow_reader.await.unwrap(), "");\n' in text


def test_a_task_named_like_the_instance_falls_back_to_a_numbered_name():
    text = on_the_clock(("@spawn", ["inbox", "receive", 5], None), ("@join", ["inbox"], ""))
    assert "    let task1 = tokio::spawn({\n" in text


def test_a_joined_void_call_stands_alone():
    text = on_the_clock(("@spawn", ["t", "leave"], None), ("@join", ["t"], None))
    assert clock_body(text).endswith("    t.await.unwrap();\n")


def test_advance_settles_itself_and_now_runs_nothing():
    text = on_the_clock(("@advance", [5], None), ("@now", [], 5), ("publish", ["a"], 1))
    assert clock_body(text) == (
        "    let start = Instant::now();\n"
        "    let mut inbox = Inbox::new();\n"
        "    settle().await;\n"
        "    advance(5).await;\n"
        "    assert_eq!(start.elapsed().as_millis(), 5);\n"
        '    assert_eq!(inbox.publish("a".to_string()), 1);\n'
    )


def test_a_long_awaited_call_breaks_into_a_chain_one_link_per_line():
    long = replace(
        method("receiveFromTheMailbox", 1, "waitMs: long; label: string", "string"),
        is_async=True,
    )
    meta = project_meta(
        ClassSignature("InventoryOfThingsAndStuff", (), (long,)),
        OPS,
        Language.RUST,
        clock=ProjectClock.VIRTUAL,
    )
    case = ops_case(
        "ex1",
        1,
        ("receiveFromTheMailbox", [10, "abc"], "a"),
        class_name="InventoryOfThingsAndStuff",
    )
    assert clock_body(generated(case, meta=meta)).endswith(
        "    assert_eq!(\n"
        "        inventory_of_things_and_stuff\n"
        '            .receive_from_the_mailbox(10, "abc".to_string())\n'
        "            .await,\n"
        '        "a"\n'
        "    );\n"
    )


@pytest.mark.parametrize("case_id", ["advance", "settle", "sorted", "assert_close"])
def test_a_case_named_like_a_helper_is_prefixed(case_id):
    case = ops_case(case_id, 1, ("@advance", [5], None), class_name="Inbox")
    assert f"async fn case_{case_id}() {{\n" in generated(case, meta=CLOCK_META)
