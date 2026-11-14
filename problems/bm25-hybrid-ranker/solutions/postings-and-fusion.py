from math import log


def hybrid_rank(
    documents: list[list[str]],
    query: list[str],
    vector_hits: list[int],
    vector_scores: list[float],
    k1: float,
    b: float,
    rrf_k: int,
    top_n: int,
) -> list[int]:
    keyword_scores = _bm25_scores(documents, query, k1, b)
    similarity = dict(zip(vector_hits, vector_scores, strict=True))
    fused: dict[int, float] = {}
    for scores in (keyword_scores, similarity):
        for rank, document in enumerate(_best_first(scores), start=1):
            fused[document] = fused.get(document, 0.0) + 1 / (rrf_k + rank)
    return _best_first(fused)[:top_n]


def _best_first(scores: dict[int, float]) -> list[int]:
    return sorted(scores, key=lambda document: (-scores[document], document))


def _bm25_scores(
    documents: list[list[str]], query: list[str], k1: float, b: float
) -> dict[int, float]:
    """Scores of the documents with a query term; the others get no entry, and so no rank."""
    # A dict and not a set, so that the terms add up in the same order on every run.
    postings: dict[str, dict[int, int]] = {term: {} for term in dict.fromkeys(query)}
    for document, tokens in enumerate(documents):
        for token in tokens:
            if token in postings:
                postings[token][document] = postings[token].get(document, 0) + 1

    document_count = len(documents)
    average_length = sum(map(len, documents)) / document_count
    scores: dict[int, float] = {}
    for counts in postings.values():
        holders = len(counts)
        idf = log(1 + (document_count - holders + 0.5) / (holders + 0.5))
        for document, count in counts.items():
            # A holder has at least one token, so the average length is above zero here.
            length_ratio = len(documents[document]) / average_length
            saturation = count + k1 * (1 - b + b * length_ratio)
            scores[document] = scores.get(document, 0.0) + idf * count * (k1 + 1) / saturation
    return scores
