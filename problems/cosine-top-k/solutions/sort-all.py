from math import sqrt, sumprod


def top_k_cosine(query: list[float], documents: list[list[float]], k: int) -> list[int]:
    query_norm = _norm(query)
    if query_norm == 0:
        return []
    # (-score, index) sorts best first, and equal scores by the lower index.
    scored = [
        (-(sumprod(query, document) / (query_norm * document_norm)), index)
        for index, document in enumerate(documents)
        if (document_norm := _norm(document)) != 0
    ]
    scored.sort()
    return [index for _, index in scored[:k]]


def _norm(vector: list[float]) -> float:
    return sqrt(sumprod(vector, vector))
