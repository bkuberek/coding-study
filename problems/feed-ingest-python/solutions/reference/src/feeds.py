"""Reads a feed: its header, its rows, and the one reason each bad row is reported for.

Nothing here touches the database, so the rules can be tested on their own. The ASCII-only
patterns are deliberate: `\\d` and `int()` accept digits of other scripts, and `date.fromisoformat`
accepts forms that are not `YYYY-MM-DD`.
"""

import re
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date

HEADER = "id,member,date,category,amount"
FIELDS = 5

DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")
AMOUNT = re.compile(r"(-?)([0-9]{1,9})(?:\.([0-9]{1,2}))?")

WRONG_FIELD_COUNT = "wrong_field_count"
EMPTY_FIELD = "empty_field"
BAD_DATE = "bad_date"
UNKNOWN_CATEGORY = "unknown_category"
BAD_AMOUNT = "bad_amount"
NEGATIVE_AMOUNT = "negative_amount"
DUPLICATE_ID = "duplicate_id"


@dataclass(frozen=True)
class Purchase:
    id: str
    member: str
    day: date
    category: str
    amount_cents: int


@dataclass(frozen=True)
class Reject:
    line: int
    reason: str


@dataclass(frozen=True)
class Feed:
    rows: int
    purchases: list[Purchase]
    rejects: list[Reject]


def lines_of(text: str) -> list[str]:
    """The lines of `text`. Only `\\n` and `\\r\\n` end a line, unlike `str.splitlines`."""
    return [line.removesuffix("\r") for line in text.split("\n")]


def parse_day(text: str) -> date | None:
    found = DATE.fullmatch(text)
    if found is None:
        return None
    year, month, day = map(int, found.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_cents(text: str) -> int | str:
    """The amount in whole cents, or the reason it is refused. Integer arithmetic only."""
    found = AMOUNT.fullmatch(text)
    if found is None:
        return BAD_AMOUNT
    sign, whole, fraction = found.groups()
    if sign:
        return NEGATIVE_AMOUNT
    return int(whole) * 100 + int((fraction or "").ljust(2, "0"))


def check_row(line: str, categories: Collection[str]) -> Purchase | str:
    """The purchase on `line`, or the first rule it breaks. Duplicates are the feed's concern."""
    fields = line.split(",")
    if len(fields) != FIELDS:
        return WRONG_FIELD_COUNT
    id_, member, day_text, category, amount_text = fields
    if not id_ or not member:
        return EMPTY_FIELD
    day = parse_day(day_text)
    if day is None:
        return BAD_DATE
    if category not in categories:
        return UNKNOWN_CATEGORY
    cents = parse_cents(amount_text)
    if isinstance(cents, str):
        return cents
    return Purchase(id_, member, day, category, cents)


def read_feed(text: str, categories: Collection[str]) -> Feed | None:
    """The feed in `text`, or None when its header is not the one the program expects."""
    lines = lines_of(text)
    if lines[0] != HEADER:
        return None
    purchases: list[Purchase] = []
    rejects: list[Reject] = []
    seen: set[str] = set()
    rows = 0
    for number, line in enumerate(lines[1:], start=2):
        if not line:
            continue
        rows += 1
        checked = check_row(line, categories)
        if isinstance(checked, str):
            rejects.append(Reject(number, checked))
        elif checked.id in seen:
            rejects.append(Reject(number, DUPLICATE_ID))
        else:
            seen.add(checked.id)
            purchases.append(checked)
    return Feed(rows, purchases, rejects)
