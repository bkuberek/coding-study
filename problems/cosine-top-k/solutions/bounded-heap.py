from heapq import heappush, heapreplace
from math import sqrt, sumprod


def top_k_cosine(query: list[float], documents: list[list[float]], k: int) -> list[int]:
    query_norm = _norm(query)
    if query_norm == 0:
        return []
    # Entries are (score, -index), so the root is the weakest document kept: the lowest score,
    # and among equal scores the highest index, which the tie-break gives up first.
    kept: list[tuple[float, int]] = []
    for index, document in enumerate(documents):
        document_norm = _norm(document)
        if document_norm == 0:
            continue
        entry = (sumprod(query, document) / (query_norm * document_norm), -index)
        if len(kept) < k:
            heappush(kept, entry)
        elif entry > kept[0]:
            heapreplace(kept, entry)
    return [-negated_index for _, negated_index in sorted(kept, reverse=True)]


def _norm(vector: list[float]) -> float:
    return sqrt(sumprod(vector, vector))
