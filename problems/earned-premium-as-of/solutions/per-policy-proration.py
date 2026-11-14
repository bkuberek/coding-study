from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def earned_premium(premiums: list[Decimal], terms: list[list[date]], valuation_date: date) -> Decimal:
    total = Decimal(0)
    for premium, (start, end) in zip(premiums, terms, strict=True):
        term_days = (end - start).days
        earned_days = min(max((valuation_date - start).days, 0), term_days)
        # Each policy is rounded to cents on its own; the book total is the sum of rounded amounts.
        total += (premium * earned_days / term_days).quantize(CENT, rounding=ROUND_HALF_UP)
    return total
