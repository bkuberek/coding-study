from collections import Counter
from math import log


class ForgettableIndex:
    def __init__(self, k1: float, b: float) -> None:
        self._k1 = k1
        self._b = b
        self._terms: dict[str, list[str]] = {}
        """Each document's distinct terms: what forgetting it must take out of the postings."""
        self._lengths: dict[str, int] = {}
        self._postings: dict[str, dict[str, int]] = {}
        """Term to the documents that hold it, with how many times each holds it."""
        self._total_length = 0

    def add(self, doc_id: str, tokens: list[str]) -> bool:
        if doc_id in self._lengths:
            return False
        self._index(doc_id, tokens)
        return True

    def update(self, doc_id: str, tokens: list[str]) -> bool:
        if doc_id not in self._lengths:
            return False
        self._unindex(doc_id)
        self._index(doc_id, tokens)
        return True

    def forget(self, doc_id: str) -> bool:
        if doc_id not in self._lengths:
            return False
        self._unindex(doc_id)
        return True

    def search(self, query: list[str], top_n: int) -> list[str]:
        scores = self._scores(query)
        return sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))[:top_n]

    def score(self, query: list[str], doc_id: str) -> float:
        return self._scores(query).get(doc_id, 0.0)

    def _index(self, doc_id: str, tokens: list[str]) -> None:
        counts = Counter(tokens)
        for term, count in counts.items():
            self._postings.setdefault(term, {})[doc_id] = count
        self._terms[doc_id] = list(counts)
        self._lengths[doc_id] = len(tokens)
        self._total_length += len(tokens)

    def _unindex(self, doc_id: str) -> None:
        for term in self._terms.pop(doc_id):
            holders = self._postings[term]
            del holders[doc_id]
            if not holders:
                del self._postings[term]
        self._total_length -= self._lengths.pop(doc_id)

    def _scores(self, query: list[str]) -> dict[str, float]:
        """BM25 scores of the documents that hold a query term; the others get no entry."""
        if self._total_length == 0:
            return {}  # no document holds a single token, so none holds a query term
        document_count = len(self._lengths)
        average_length = self._total_length / document_count
        scores: dict[str, float] = {}
        # A dict and not a set, so that the terms add up in the same order on every run.
        for term in dict.fromkeys(query):
            holders = self._postings.get(term, {})
            idf = log(1 + (document_count - len(holders) + 0.5) / (len(holders) + 0.5))
            for doc_id, count in holders.items():
                length_ratio = self._lengths[doc_id] / average_length
                saturation = count + self._k1 * (1 - self._b + self._b * length_ratio)
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * count * (self._k1 + 1) / saturation
        return scores
