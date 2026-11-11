import pytest

from redaction.scoring import score
from redaction.spans import Span

EMAIL = Span(0, 5, "EMAIL")
PHONE = Span(8, 20, "PHONE")


def test_everything_found_and_nothing_else_is_perfect() -> None:
    assert score([EMAIL, PHONE], [PHONE, EMAIL]) == [1.0, 1.0, 1.0]


def test_nothing_chosen_has_perfect_precision_and_no_recall() -> None:
    assert score([], [EMAIL]) == [1.0, 0.0, 0.0]


def test_nothing_to_find_but_something_chosen_has_perfect_recall_and_no_precision() -> None:
    assert score([EMAIL], []) == [0.0, 1.0, 0.0]


def test_nothing_on_either_side_is_perfect() -> None:
    assert score([], []) == [1.0, 1.0, 1.0]


@pytest.mark.parametrize("near", [Span(0, 4, "EMAIL"), Span(1, 5, "EMAIL"), Span(0, 5, "PHONE")])
def test_a_span_that_is_not_the_same_in_start_end_and_label_is_both_wrong_and_missed(
    near: Span,
) -> None:
    assert score([near], [EMAIL]) == [0.0, 0.0, 0.0]


def test_a_span_chosen_twice_is_right_once() -> None:
    precision, recall, _ = score([EMAIL, EMAIL], [EMAIL])

    assert (precision, recall) == (0.5, 1.0)


def test_missing_half_costs_more_than_adding_as_many_spans_as_were_right() -> None:
    missing_half = score([EMAIL], [EMAIL, PHONE])[2]
    adding_as_many = score([EMAIL, PHONE, Span(30, 33, "PERSON"), Span(40, 43, "PERSON")], [EMAIL, PHONE])[2]

    assert missing_half == pytest.approx(5 * 0.5 / (4 * 1 + 0.5))
    assert adding_as_many == pytest.approx(5 * 0.5 * 1 / (4 * 0.5 + 1))
    assert adding_as_many > missing_half
