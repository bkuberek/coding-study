from decimal import Decimal


def calculate_tax(brackets: list[list[int]], income: int) -> Decimal:
    cents = 0  # tax in hundredths of a unit: every rate is a whole percent
    lower = 0
    for upper, percent in brackets:
        if lower >= income:
            break
        cents += (min(upper, income) - lower) * percent
        lower = upper
    return Decimal(cents).scaleb(-2)
