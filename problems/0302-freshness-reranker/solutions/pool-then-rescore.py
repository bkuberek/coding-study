HALF = 0.5
NO_BOOST = 1.0


def rerank_by_freshness(
    candidates: list[list[str]],
    relevance: list[float],
    age_hours: list[float],
    half_life_hours: float,
    boost_sources: list[str],
    boost_factors: list[float],
    pool_size: int,
) -> list[str]:
    boost_of = dict(zip(boost_sources, boost_factors, strict=True))
    pool = sorted(range(len(candidates)), key=lambda index: (-relevance[index], index))[:pool_size]
    # For each canonical id, the (negated score, index) of its best copy: smaller is better.
    best_copy: dict[str, tuple[float, int]] = {}
    for index in pool:
        _, canonical_id, source = candidates[index]
        decay = HALF ** (age_hours[index] / half_life_hours)
        rank_key = (-(relevance[index] * decay * boost_of.get(source, NO_BOOST)), index)
        if canonical_id not in best_copy or rank_key < best_copy[canonical_id]:
            best_copy[canonical_id] = rank_key
    return [candidates[index][0] for _, index in sorted(best_copy.values())]
