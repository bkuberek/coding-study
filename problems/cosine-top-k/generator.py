"""Seeded inputs for cosine-top-k: n documents of DIMENSION whole numbers each.

At ladder sizes k is fixed at LADDER_K, so the work grows with n alone: one pass over the
documents costs O(n m), a heap of k adds O(n log k) and sorting everything adds O(n log n).
Small inputs, the oracle's, vary k from 1 to past the number of documents and hold the cases
a tie-break needs: an exact copy or a doubled copy of an earlier document (whose score is
exactly equal however the arithmetic is ordered, since doubling is exact), zero documents, and
now and then a zero query.

validate checks that no two scores near the cut differ by a rounding error, so the expected
order never depends on how a solution orders its arithmetic.
"""

import random
from math import sqrt

DIMENSION = 8
LADDER_K = 10
SMALL = 30
COMPONENT_LIMIT = 100
ZERO_DOCUMENT_SHARE = 0.02
COPY_SHARE = 0.15
ZERO_QUERY_SHARE = 0.05
MAX_DOCUMENTS = 10**5
MAX_DIMENSION = 256
MAX_NUMBERS = 10**6
MAX_K = 1000
VALUE_LIMIT = 1000
TIE_GAP = 1e-9


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_DOCUMENTS)
    small = count <= SMALL
    documents: list[list[float]] = []
    # Only fresh vectors are copied, so a doubled copy is never doubled again past the limit.
    fresh: list[list[float]] = []
    for _ in range(count):
        roll = rng.random()
        if roll < ZERO_DOCUMENT_SHARE:
            documents.append([0.0] * DIMENSION)
        elif small and fresh and roll < COPY_SHARE:
            factor = rng.choice((1.0, 2.0))
            documents.append([factor * value for value in rng.choice(fresh)])
        else:
            fresh.append(_vector(rng))
            documents.append(fresh[-1])
    zero_query = small and rng.random() < ZERO_QUERY_SHARE
    query = [0.0] * DIMENSION if zero_query else _vector(rng)
    k = rng.randint(1, count + 2) if small else LADDER_K
    return {"query": query, "documents": documents, "k": k}


def _vector(rng: random.Random) -> list[float]:
    vector = [float(rng.randint(-COMPONENT_LIMIT, COMPONENT_LIMIT)) for _ in range(DIMENSION)]
    if not any(vector):
        vector[0] = 1.0
    return vector


def validate(case_input: dict) -> None:
    query, documents, k = case_input["query"], case_input["documents"], case_input["k"]
    dimension = len(query)
    assert 1 <= len(documents) <= MAX_DOCUMENTS, "document count out of range"
    assert 1 <= dimension <= MAX_DIMENSION, "dimension out of range"
    assert len(documents) * dimension <= MAX_NUMBERS, "too many numbers"
    assert 1 <= k <= MAX_K, "k out of range"
    for vector in [query, *documents]:
        assert len(vector) == dimension, "every vector has the query's dimension"
        assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in vector), "value out of range"
    _assert_no_near_tie_at_the_cut(query, documents, k)


def _assert_no_near_tie_at_the_cut(
    query: list[float], documents: list[list[float]], k: int
) -> None:
    query_norm = _norm(query)
    if query_norm == 0:
        return
    scores = sorted(
        (
            _dot(query, document) / (query_norm * _norm(document))
            for document in documents
            if any(document)
        ),
        reverse=True,
    )
    leading = scores[: k + 1]
    for higher, lower in zip(leading, leading[1:], strict=False):
        exact_tie_or_clear_gap = higher == lower or higher - lower > TIE_GAP
        assert exact_tie_or_clear_gap, "two scores near the cut differ by rounding"


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _norm(vector: list[float]) -> float:
    return sqrt(_dot(vector, vector))
