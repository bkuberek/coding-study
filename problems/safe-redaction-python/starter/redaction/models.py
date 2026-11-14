"""The types the extractor speaks in."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Proposal:
    """A stretch of text the extractor says is personal data.

    `start` is where it begins and `end` is where it stops (not included), `label` says what it
    found (`EMAIL`, `PHONE`, `PERSON`), and `quote` is the text the extractor says it saw there.
    Nothing promises that the text at `start:end` is `quote`.
    """

    start: int
    end: int
    label: str
    quote: str
