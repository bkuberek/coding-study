def subsets_with_dup(nums: list[int]) -> list[list[int]]:
    ordered = sorted(nums)
    result: list[list[int]] = []
    chosen: list[int] = []

    def extend(start: int) -> None:
        # Every node of this recursion is a distinct subset.
        result.append(chosen.copy())
        for i in range(start, len(ordered)):
            # A second copy at the same level would rebuild the first copy's subtree.
            if i > start and ordered[i] == ordered[i - 1]:
                continue
            chosen.append(ordered[i])
            extend(i + 1)
            chosen.pop()

    extend(0)
    return result
