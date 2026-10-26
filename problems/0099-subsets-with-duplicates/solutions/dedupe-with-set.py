def subsets_with_dup(nums: list[int]) -> list[list[int]]:
    ordered = sorted(nums)
    # Taking values in sorted order gives every multiset one canonical tuple to dedupe on.
    distinct = {
        tuple(value for i, value in enumerate(ordered) if mask >> i & 1)
        for mask in range(1 << len(ordered))
    }
    return [list(subset) for subset in distinct]
