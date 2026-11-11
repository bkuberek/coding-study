"""The safety net: two patterns for what the extractor most often misses."""

import re

from redaction.spans import Span

EMAIL = re.compile(r"[\w.%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
PHONE = re.compile(
    r"(?<![\w+])(?:\+?[0-9]{1,3}[ .-])?(?:\([0-9]{3}\)|[0-9]{3})[ .-]?[0-9]{3}[ .-]?[0-9]{4}(?!\w)"
)


def found_by_patterns(text: str) -> list[Span]:
    """Every email, then every phone number, in the order of the text."""
    emails = [Span(m.start(), m.end(), "EMAIL") for m in EMAIL.finditer(text)]
    phones = [Span(m.start(), m.end(), "PHONE") for m in PHONE.finditer(text)]
    return emails + phones
