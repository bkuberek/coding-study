import pytest

from coding_study.domain.value_text import MAX_VALUE_TEXT, truncate, value_text


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
