from calendar import monthrange
from datetime import date
from decimal import Decimal


def installment_schedule(premium: Decimal, installment_count: int, first_due_date: date) -> list[list[str]]:
    if installment_count == 0:
        return []
    cents = int(premium * 100)  # exact: the premium has at most two fractional digits
    base, leftover = divmod(cents, installment_count)
    schedule = []
    for number in range(installment_count):
        amount = base + 1 if number < leftover else base  # leftover cents go to the first installments
        due = add_months(first_due_date, number)
        schedule.append([due.isoformat(), f"{amount // 100}.{amount % 100:02d}"])
    return schedule


def add_months(anchor: date, months: int) -> date:
    # Counted from the anchor, never from the previous due date, so 31 Jan -> 28 Feb -> 31 Mar.
    month_index = anchor.month - 1 + months
    year, month = anchor.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(anchor.day, monthrange(year, month)[1]))
