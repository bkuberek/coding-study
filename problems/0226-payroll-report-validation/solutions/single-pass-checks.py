import re
from datetime import date
from decimal import Decimal

FIELDS = ("contractorId", "classCode", "payroll", "periodStart")
# [0-9], never \d: in Python \d also matches other scripts' digits.
CONTRACTOR_ID = re.compile(r"[a-z0-9-]{1,20}")
CLASS_CODE = re.compile(r"[0-9]{4}")
PAYROLL = re.compile(r"[0-9]+(\.[0-9]{1,2})?")
ISO_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
MAX_PAYROLL = Decimal(1_000_000_000)
FIRST_DAY, LAST_DAY = date(2000, 1, 1), date(2099, 12, 31)


def validate_rows(rows: list[list[str]]) -> list[str]:
    errors: list[str] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows):
        if len(row) != len(FIELDS):
            errors.append(f"{index}:row:column-count")
            continue
        contractor_id, class_code, payroll, period_start = row
        reasons = [
            check_pattern(contractor_id, CONTRACTOR_ID),
            check_pattern(class_code, CLASS_CODE),
            check_payroll(payroll),
            check_period_start(period_start),
        ]
        errors.extend(f"{index}:{field}:{reason}" for field, reason in zip(FIELDS, reasons) if reason)
        if not (reasons[0] or reasons[1] or reasons[3]):
            key = (contractor_id, class_code, period_start)
            if key in seen_keys:
                errors.append(f"{index}:row:duplicate")
            seen_keys.add(key)
    return errors


def check_pattern(value: str, pattern: re.Pattern[str]) -> str:
    if not value:
        return "missing"
    return "" if pattern.fullmatch(value) else "invalid"


def check_payroll(value: str) -> str:
    reason = check_pattern(value, PAYROLL)
    if reason:
        return reason
    return "" if 0 < Decimal(value) <= MAX_PAYROLL else "out-of-range"


def check_period_start(value: str) -> str:
    reason = check_pattern(value, ISO_DAY)
    if reason:
        return reason
    try:
        day = date.fromisoformat(value)  # the pattern runs first: fromisoformat also accepts 20260101
    except ValueError:
        return "invalid"
    return "" if FIRST_DAY <= day <= LAST_DAY else "out-of-range"
