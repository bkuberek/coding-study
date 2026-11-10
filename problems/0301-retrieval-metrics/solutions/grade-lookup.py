from math import log2

RELEVANT_GRADE = 1
METRIC_COUNT = 3


def retrieval_metrics(
    rankings: list[list[str]], judged_docs: list[list[str]], grades: list[list[int]], k: int
) -> list[float]:
    per_query = [
        _query_metrics(ranking[:k], dict(zip(docs, query_grades, strict=True)), k)
        for ranking, docs, query_grades in zip(rankings, judged_docs, grades, strict=True)
    ]
    scored = [metrics for metrics in per_query if metrics is not None]
    if not scored:
        return [0.0] * METRIC_COUNT
    return [sum(column) / len(scored) for column in zip(*scored, strict=True)]


def _query_metrics(
    top: list[str], grade_of: dict[str, int], k: int
) -> tuple[float, float, float] | None:
    """Recall, reciprocal rank and nDCG at k for one query, or None when nothing is relevant."""
    relevant = sum(1 for grade in grade_of.values() if grade >= RELEVANT_GRADE)
    if relevant == 0:
        return None
    retrieved = [grade_of.get(doc, 0) for doc in top]
    found = sum(1 for grade in retrieved if grade >= RELEVANT_GRADE)
    first_rank = next(
        (rank for rank, grade in enumerate(retrieved, start=1) if grade >= RELEVANT_GRADE), None
    )
    reciprocal_rank = 0.0 if first_rank is None else 1 / first_rank
    # The ideal ranking orders every judged document, retrieved or not, by grade.
    ideal = sorted(grade_of.values(), reverse=True)[:k]
    return found / relevant, reciprocal_rank, _dcg(retrieved) / _dcg(ideal)


def _dcg(grades: list[int]) -> float:
    return sum((2**grade - 1) / log2(rank + 1) for rank, grade in enumerate(grades, start=1))
