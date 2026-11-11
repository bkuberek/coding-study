from datetime import date

import pytest
from feeds import HEADER, Purchase, Reject, parse_cents, read_feed

CATEGORIES = {"grocery", "fuel"}


@pytest.mark.parametrize(
    ("text", "cents"),
    [("12", 1200), ("12.5", 1250), ("12.05", 1205), ("0.29", 29), ("1.15", 115), ("4.35", 435)],
)
def test_an_amount_becomes_cents_without_a_float(text: str, cents: int) -> None:
    assert parse_cents(text) == cents


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", "bad_amount"),
        ("1,000", "bad_amount"),
        ("12.345", "bad_amount"),
        ("５", "bad_amount"),
        ("-5", "negative_amount"),
        ("-0.00", "negative_amount"),
    ],
)
def test_an_amount_that_is_not_a_plain_number_is_refused_with_its_reason(
    text: str, reason: str
) -> None:
    assert parse_cents(text) == reason


def test_the_first_rule_a_row_breaks_names_it() -> None:
    feed = read_feed(f"{HEADER}\nT1,ana,2027-02-30,nope,abc\n", CATEGORIES)

    assert feed is not None
    assert feed.rejects == [Reject(2, "bad_date")]


def test_a_row_counts_as_a_duplicate_only_of_a_row_that_passed() -> None:
    text = f"{HEADER}\nT1,ana,2027-13-01,fuel,5\nT1,ana,2027-03-01,fuel,5\nT1,ana,2027-03-02,fuel,6\n"

    feed = read_feed(text, CATEGORIES)

    assert feed is not None
    assert feed.purchases == [Purchase("T1", "ana", date(2027, 3, 1), "fuel", 500)]
    assert feed.rejects == [Reject(2, "bad_date"), Reject(4, "duplicate_id")]


def test_empty_lines_are_not_rows_but_they_are_lines() -> None:
    feed = read_feed(f"{HEADER}\r\n\r\nT1,ana,2027-03-01,fuel,x\r\n", CATEGORIES)

    assert feed is not None
    assert (feed.rows, feed.rejects) == (1, [Reject(3, "bad_amount")])


def test_a_vertical_tab_does_not_end_a_line() -> None:
    feed = read_feed(f"{HEADER}\nT1,ana,2027-03-01,fuel\x0b,5\nT2,ana,2027-03-01,fuel,5\n", CATEGORIES)

    assert feed is not None
    assert feed.rejects == [Reject(2, "unknown_category")]
    assert [purchase.id for purchase in feed.purchases] == ["T2"]


def test_a_wrong_header_means_no_feed() -> None:
    assert read_feed("member,id,date,category,amount\nT1,ana,2027-03-01,fuel,5\n", CATEGORIES) is None
