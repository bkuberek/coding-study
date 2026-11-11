"""Spans, and the one way text is rewritten around them."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    """The characters `start` up to, and not including, `end` of a text, with a label."""

    start: int
    end: int
    label: str

    @property
    def length(self) -> int:
        return self.end - self.start


def apply(text: str, spans: Iterable[Span]) -> str:
    """`text` with each span written as `[LABEL]`. The spans must not overlap.

    The result is built from pieces: the text between spans is copied, and each label is written
    where its span was. Nothing is replaced inside a string that is already changing, so an
    offset never has to be moved when an earlier span turns out longer or shorter than its label.
    """
    pieces: list[str] = []
    cursor = 0
    for span in sorted(spans, key=lambda span: span.start):
        pieces.append(text[cursor : span.start])
        pieces.append(f"[{span.label}]")
        cursor = span.end
    pieces.append(text[cursor:])
    return "".join(pieces)
