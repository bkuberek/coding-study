from decimal import Decimal


def calculate_tax(brackets: list[list[int]], income: int) -> Decimal:
    cents = 0  # tax in hundredths of a unit: every rate is a whole percent
    bracket = 0
    for unit in range(income):
        # Unit number unit covers income from unit to unit + 1.
        while brackets[bracket][0] <= unit:
            bracket += 1
        cents += brackets[bracket][1]
    return Decimal(cents).scaleb(-2)
