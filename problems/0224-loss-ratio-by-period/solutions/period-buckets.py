from datetime import date
from decimal import ROUND_HALF_UP, Decimal

RATIO_STEP = Decimal("0.0001")
NO_EARNED_PREMIUM = Decimal(-1)


def loss_ratios(
    earned_dates: list[date],
    earned_amounts: list[Decimal],
    loss_dates: list[date],
    loss_amounts: list[Decimal],
    from_date: date,
    to_date: date,
    period_months: int,
) -> list[Decimal]:
    first = period_index(from_date, period_months)
    count = period_index(to_date, period_months) - first + 1
    earned = sum_by_period(earned_dates, earned_amounts, period_months, first, count)
    losses = sum_by_period(loss_dates, loss_amounts, period_months, first, count)
    return [
        NO_EARNED_PREMIUM if premium == 0 else (loss / premium).quantize(RATIO_STEP, rounding=ROUND_HALF_UP)
        for premium, loss in zip(earned, losses)
    ]


def period_index(day: date, period_months: int) -> int:
    # Periods are calendar-aligned blocks of months counted from January of year 0.
    return (day.year * 12 + day.month - 1) // period_months


def sum_by_period(
    dates: list[date], amounts: list[Decimal], period_months: int, first: int, count: int
) -> list[Decimal]:
    totals = [Decimal(0)] * count
    for day, amount in zip(dates, amounts, strict=True):
        slot = period_index(day, period_months) - first
        if 0 <= slot < count:
            totals[slot] += amount
    return totals
