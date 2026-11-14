"""Deciding which of the extractor's proposals to believe, and where they really are."""

from redaction.models import Proposal
from redaction.spans import Span


def nearest_occurrence(text: str, quote: str, near: int) -> int | None:
    """Where `quote` occurs in `text` closest to `near`; the earlier one when two are as close."""
    best: int | None = None
    at = text.find(quote)
    while at != -1:
        if best is None or abs(at - near) < abs(best - near):
            best = at
        at = text.find(quote, at + 1)
    return best


def believed(text: str, proposal: Proposal) -> Span | None:
    """The span a proposal stands for, or None when nothing can be said about where it is.

    A proposal whose offsets cut out exactly its quote is believed as it is. One whose offsets do
    not is moved to the nearest place its quote really occurs. One whose quote is nowhere in the
    text, or empty, cannot be placed and is dropped.
    """
    start, end, label, quote = proposal.start, proposal.end, proposal.label, proposal.quote
    if 0 <= start < end <= len(text) and text[start:end] == quote:
        return Span(start, end, label)
    if not quote:
        return None
    at = nearest_occurrence(text, quote, start)
    return None if at is None else Span(at, at + len(quote), label)


def merge(spans: list[Span]) -> list[Span]:
    """Spans that share a character become one span covering all of them.

    Touching spans do not share a character and stay apart. A merged span takes the label of the
    longest span that went into it; of equal lengths the one that starts first, and of those the
    one that came first in `spans`.
    """
    ordered = sorted(enumerate(spans), key=lambda item: (item[1].start, item[1].end))
    merged: list[Span] = []
    group: list[tuple[int, Span]] = []
    group_end = 0
    for item in ordered:
        span = item[1]
        if group and span.start >= group_end:
            merged.append(_union(group))
            group = []
        group_end = max(group_end, span.end) if group else span.end
        group.append(item)
    if group:
        merged.append(_union(group))
    return merged


def _union(group: list[tuple[int, Span]]) -> Span:
    winner = max(group, key=lambda item: (item[1].length, -item[1].start, -item[0]))[1]
    return Span(
        min(span.start for _, span in group),
        max(span.end for _, span in group),
        winner.label,
    )
