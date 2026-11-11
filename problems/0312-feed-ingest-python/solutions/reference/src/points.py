"""What purchases earn. Pure functions over integers: no floats, no database.

A category pays a percentage of the base rate (1 point per 100 cents) on each band of what the
member has spent in it so far this calendar month. A band is a range of that running monthly total,
so a purchase that crosses a band's edge is paid at both rates. Each purchase's points are rounded
down on their own.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

CENTS_PER_POINT = 100
PERCENT = 100

# (upper edge of the band in cents of monthly spend, or None for no limit, percent of the base rate)
BANDS: dict[str, list[tuple[int | None, int]]] = {
    "grocery": [(20_000, 200), (None, 100)],
    "dining": [(10_000, 300), (30_000, 200), (None, 100)],
    "fuel": [(15_000, 150), (None, 100)],
    "travel": [(50_000, 400), (None, 150)],
    "other": [(None, 100)],
}


@dataclass(frozen=True)
class Spend:
    id: str
    day: date
    category: str
    cents: int


def weighted_cents(category: str, spent_before: int, cents: int) -> int:
    """Each cent of the purchase times the percent of the band it falls in."""
    start, end = spent_before, spent_before + cents
    lower, total = 0, 0
    for upper, percent in BANDS[category]:
        top = end if upper is None else min(end, upper)
        total += max(0, top - max(start, lower)) * percent
        if upper is None:
            break
        lower = upper
    return total


def points_per_month(spends: Iterable[Spend]) -> dict[str, int]:
    """One member's points for each month (`YYYY-MM`) they bought in.

    Purchases are taken in the order of their date, then of their id compared as plain text.
    """
    spent: dict[tuple[str, str], int] = defaultdict(int)
    earned: dict[str, int] = defaultdict(int)
    for spend in sorted(spends, key=lambda spend: (spend.day, spend.id)):
        month = spend.day.isoformat()[:7]
        before = spent[(month, spend.category)]
        weighted = weighted_cents(spend.category, before, spend.cents)
        earned[month] += weighted // (CENTS_PER_POINT * PERCENT)
        spent[(month, spend.category)] = before + spend.cents
    return dict(earned)
