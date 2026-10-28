import pytest

from coding_study.domain.type_dsl import parse_value_type
from coding_study.domain.value_text import MAX_VALUE_TEXT, display_text, truncate, value_text


@pytest.mark.parametrize(
    ("value", "text"),
    [
        ([1, 2], "[1, 2]"),
        (None, "null"),
        (True, "true"),
        ("üñ", '"üñ"'),
        ([[1], []], "[[1], []]"),
        (0.5, "0.5"),
    ],
)
def test_values_print_as_compact_json(value, text):
    assert value_text(value) == text


def test_long_values_are_truncated_to_the_report_limit():
    assert len(value_text(list(range(1000)))) == MAX_VALUE_TEXT


def test_truncated_values_end_with_an_ellipsis():
    assert value_text(list(range(1000))).endswith("...")


def test_text_at_the_limit_is_kept():
    assert truncate("abcde", 5) == "abcde"


def test_text_over_the_limit_keeps_room_for_the_ellipsis():
    assert truncate("abcdef", 5) == "ab..."


@pytest.mark.parametrize(
    ("value", "declared", "text"),
    [
        ("2500.50", "decimal", "2500.50"),
        ("2026-01-01", "date", "2026-01-01"),
        (["1.5", "-2"], "decimal[]", "[1.5, -2]"),
        ([["2026-01-01", "2026-02-01"], []], "date[][]", "[[2026-01-01, 2026-02-01], []]"),
        ([["0.1"], ["0.2", "0.3"]], "list<decimal[]>", "[[0.1], [0.2, 0.3]]"),
        ([], "list<date>", "[]"),
    ],
)
def test_decimals_and_dates_show_unquoted(value, declared, text):
    assert display_text(value, parse_value_type(declared)) == text


@pytest.mark.parametrize(
    ("value", "declared", "text"),
    [
        ("A1", "string", '"A1"'),
        (["a", "b"], "char[]", '["a", "b"]'),
        ([[1, 2], [3]], "list<int[]>", "[[1, 2], [3]]"),
        ({"values": [1, 2], "cycle_at": 0}, "ListNode", '{"values": [1, 2], "cycle_at": 0}'),
    ],
)
def test_other_types_show_as_json(value, declared, text):
    assert display_text(value, parse_value_type(declared)) == text


def test_values_without_a_declared_type_show_as_json():
    assert display_text(["2500.50"], None) == '["2500.50"]'


@pytest.mark.parametrize(
    ("value", "declared", "text"),
    [
        (2500, "decimal", "2500"),
        (None, "date", "null"),
        ("1.5", "decimal[]", '"1.5"'),
        ([None, "1.5"], "list<decimal>", "[null, 1.5]"),
    ],
)
def test_values_that_do_not_fit_their_type_show_as_json(value, declared, text):
    assert display_text(value, parse_value_type(declared)) == text
