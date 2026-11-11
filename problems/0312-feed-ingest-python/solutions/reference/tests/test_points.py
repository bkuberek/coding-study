from datetime import date

import pytest
from points import Spend, points_per_month, weighted_cents


@pytest.mark.parametrize(
    ("category", "spent_before", "cents", "points"),
    [
        ("grocery", 0, 4_250, 85),
        ("grocery", 19_000, 3_000, 40),
        ("dining", 0, 45_000, 850),
        ("travel", 0, 60_000, 2_150),
        ("other", 0, 99, 0),
        ("other", 0, 1_299, 12),
    ],
)
def test_a_purchase_is_paid_at_the_rate_of_each_band_it_covers(
    category: str, spent_before: int, cents: int, points: int
) -> None:
    assert weighted_cents(category, spent_before, cents) // 10_000 == points


def test_each_purchase_is_rounded_down_on_its_own() -> None:
    spends = [
        Spend("A", date(2027, 3, 1), "other", 150),
        Spend("B", date(2027, 3, 2), "other", 150),
    ]

    assert points_per_month(spends) == {"2027-03": 2}


def test_a_new_month_starts_the_bands_again() -> None:
    spends = [
        Spend("A", date(2027, 3, 31), "grocery", 20_000),
        Spend("B", date(2027, 4, 1), "grocery", 10_000),
    ]

    assert points_per_month(spends) == {"2027-03": 400, "2027-04": 200}


def test_purchases_of_one_day_are_taken_in_the_order_of_their_ids_as_text() -> None:
    day = date(2027, 3, 1)
    spends = [Spend("P9", day, "fuel", 14_950), Spend("P10", day, "fuel", 101)]

    # "P10" sorts before "P9", so P9 is the one that straddles the edge of the band. Taken the
    # other way round, the same two purchases earn 225.
    assert points_per_month(spends) == {"2027-03": 224}
