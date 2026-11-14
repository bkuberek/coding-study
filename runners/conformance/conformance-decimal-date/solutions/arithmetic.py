"""Conformance reference: exact decimal arithmetic with explicit rounding, and calendar days."""

from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


class DecimalDates:
    def normalized(self, value: Decimal) -> Decimal:
        return value

    def add(self, left: Decimal, right: Decimal) -> Decimal:
        return left + right

    def total(self, values: list[Decimal]) -> Decimal:
        return sum(values, Decimal(0))

    def round_half_up(self, value: Decimal) -> Decimal:
        return value.quantize(CENT, rounding=ROUND_HALF_UP)

    def round_half_even(self, value: Decimal) -> Decimal:
        return value.quantize(CENT, rounding=ROUND_HALF_EVEN)

    def prorate(self, premium: Decimal, days: int, total_days: int) -> Decimal:
        return (premium * days / total_days).quantize(CENT, rounding=ROUND_HALF_UP)

    def add_days(self, day: date, days: int) -> date:
        return day + timedelta(days=days)

    def days_between(self, start: date, end: date) -> int:
        return (end - start).days
