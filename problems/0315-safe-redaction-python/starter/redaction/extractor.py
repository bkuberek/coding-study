"""A stand-in for the model that finds personal data in text.

A real extractor is a trained model behind an API. This one is a few fixed rules, so it gives the
same answer every time and costs nothing to run, and it is unreliable in the ways such models are.
`propose(text)` returns its proposals, emails first, then phone numbers, then names, each group in
the order of the text. Its known failures:

- **Offsets in bytes.** `start` and `end` count the UTF-8 bytes before them, not the characters,
  so every proposal after a non-ASCII character such as `é` or an emoji points too far right.
- **Short emails.** It stops at the first dot of a domain (`ana@mail.example.com` is read as
  `ana@mail.example`) and does not know `+` in a name (`ana+news@x.io` is read as `news@x.io`).
- **Overlapping names.** For `Grace Hopper` it proposes the whole name and `Hopper` again.
- **Missed phone numbers.** It knows `555-123-4567` and `(555) 123-4567`, and nothing else: not
  `555.123.4567`, not `5551234567`, and for `+1 555-123-4567` it leaves the `+1 ` out.
- **A short list of first names.** It has never heard of anyone else.

Your own tests may call it. The graded cases give your code proposals as plain lists.
"""

import re

from redaction.models import Proposal

FIRST_NAMES = ("Ada", "Grace", "Alan", "Margaret", "Linus", "Katherine", "Dennis", "Barbara")

EMAIL = re.compile(r"[A-Za-z0-9._-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\(\d{3}\) \d{3}-\d{4}|\d{3}-\d{3}-\d{4}")
NAME = re.compile(r"\b(?:" + "|".join(FIRST_NAMES) + r")(?: ([A-Z][a-z]+))?\b")


def propose(text: str) -> list[Proposal]:
    """What the extractor thinks is personal data in `text`, mistakes included."""
    proposals: list[Proposal] = []
    for found in EMAIL.finditer(text):
        proposals.append(_proposal(text, found.start(), found.end(), "EMAIL"))
    for found in PHONE.finditer(text):
        proposals.append(_proposal(text, found.start(), found.end(), "PHONE"))
    for found in NAME.finditer(text):
        proposals.append(_proposal(text, found.start(), found.end(), "PERSON"))
        if found.group(1):
            proposals.append(_proposal(text, found.start(1), found.end(1), "PERSON"))
    return proposals


def _proposal(text: str, start: int, end: int, label: str) -> Proposal:
    return Proposal(_in_bytes(text, start), _in_bytes(text, end), label, text[start:end])


def _in_bytes(text: str, index: int) -> int:
    return len(text[:index].encode("utf-8"))
