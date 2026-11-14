"""Precision, recall and F2 of the spans a redactor chose against the spans it should have."""

from collections import Counter
from collections.abc import Sequence

from redaction.spans import Span

TRUE_POSITIVE_WEIGHT = 5
"""F-beta with beta 2: `(1 + beta**2) * tp` over `(1 + beta**2) * tp + beta**2 * fn + fp`."""
MISSED_WEIGHT = 4


def score(chosen: Sequence[Span], gold: Sequence[Span]) -> list[float]:
    """`[precision, recall, f2]` under exact matching.

    A chosen span matches a gold span when start, end and label are all equal, and each span of
    either list is used in at most one match, so a span chosen twice is right once. With nothing
    chosen precision is 1 (nothing wrong was claimed), and with nothing to find recall is 1.
    """
    left = Counter(chosen)
    matched = 0
    for span in gold:
        if left[span] > 0:
            left[span] -= 1
            matched += 1
    wrong, missed = len(chosen) - matched, len(gold) - matched
    precision = matched / len(chosen) if chosen else 1.0
    recall = matched / len(gold) if gold else 1.0
    weight = TRUE_POSITIVE_WEIGHT * matched
    denominator = weight + MISSED_WEIGHT * missed + wrong
    return [precision, recall, weight / denominator if denominator else 1.0]
