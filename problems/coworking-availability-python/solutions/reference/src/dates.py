"""The one form a day takes in this API."""

import re
from datetime import date

DAY_FORM = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def parse_day(text: str) -> date | None:
    """The day `text` names, written YYYY-MM-DD; None when it names no day in that form.

    The form comes first: `date.fromisoformat` alone takes `20270301` as well.
    """
    if DAY_FORM.fullmatch(text) is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
