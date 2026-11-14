def combination_sum2(candidates: list[int], target: int) -> list[list[int]]:
    ordered = sorted(candidates)
    found: set[tuple[int, ...]] = set()
    for mask in range(1 << len(ordered)):
        # Values taken in sorted order give each multiset one canonical tuple.
        chosen = tuple(value for i, value in enumerate(ordered) if mask >> i & 1)
        if sum(chosen) == target:
            found.add(chosen)
    return [list(combination) for combination in found]
