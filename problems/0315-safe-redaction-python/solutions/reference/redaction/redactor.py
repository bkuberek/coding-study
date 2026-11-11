"""The class that `cstudy submit` and the tests drive."""

from redaction.models import Proposal
from redaction.net import found_by_patterns
from redaction.scoring import score
from redaction.spans import Span, apply
from redaction.trust import believed, merge


def _spans(starts: list[int], ends: list[int], labels: list[str]) -> list[Span]:
    return [Span(*parts) for parts in zip(starts, ends, labels, strict=True)]


def _proposals(
    starts: list[int], ends: list[int], labels: list[str], quotes: list[str]
) -> list[Proposal]:
    return [Proposal(*parts) for parts in zip(starts, ends, labels, quotes, strict=True)]


def _believed(text: str, proposals: list[Proposal]) -> list[Span]:
    placed = (believed(text, proposal) for proposal in proposals)
    return [span for span in placed if span is not None]


def _trusted(text: str, proposals: list[Proposal]) -> list[Span]:
    return merge(_believed(text, proposals))


def _safe(text: str, proposals: list[Proposal]) -> list[Span]:
    """What to hide: the believed proposals, then the patterns' finds, merged in that order."""
    return merge(_believed(text, proposals) + found_by_patterns(text))


class Redactor:
    def redact(self, text: str, starts: list[int], ends: list[int], labels: list[str]) -> str:
        return apply(text, _spans(starts, ends, labels))

    def redact_proposed(
        self, text: str, starts: list[int], ends: list[int], labels: list[str], quotes: list[str]
    ) -> str:
        return apply(text, _trusted(text, _proposals(starts, ends, labels, quotes)))

    def redact_safely(
        self, text: str, starts: list[int], ends: list[int], labels: list[str], quotes: list[str]
    ) -> str:
        return apply(text, _safe(text, _proposals(starts, ends, labels, quotes)))

    def score(
        self,
        starts: list[int],
        ends: list[int],
        labels: list[str],
        gold_starts: list[int],
        gold_ends: list[int],
        gold_labels: list[str],
    ) -> list[float]:
        return score(_spans(starts, ends, labels), _spans(gold_starts, gold_ends, gold_labels))

    def evaluate(
        self,
        text: str,
        starts: list[int],
        ends: list[int],
        labels: list[str],
        quotes: list[str],
        gold_starts: list[int],
        gold_ends: list[int],
        gold_labels: list[str],
    ) -> list[float]:
        chosen = _safe(text, _proposals(starts, ends, labels, quotes))
        return score(chosen, _spans(gold_starts, gold_ends, gold_labels))
