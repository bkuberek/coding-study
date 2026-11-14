from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
OUTSIDE_TERM = Decimal(-1)


def unearned_premium(term_premium: Decimal, term_start: date, term_end: date, change_date: date) -> Decimal:
    if not term_start <= change_date <= term_end:
        return OUTSIDE_TERM
    remaining = (term_end - change_date).days
    term_days = (term_end - term_start).days
    return (term_premium * remaining / term_days).quantize(CENT, rounding=ROUND_HALF_UP)
