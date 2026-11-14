def combination_sum(candidates: list[int], target: int) -> list[list[int]]:
    ordered = sorted(candidates)
    result: list[list[int]] = []
    chosen: list[int] = []

    def extend(start: int, remaining: int) -> None:
        if remaining == 0:
            result.append(chosen.copy())
            return
        # Values are added in non-decreasing order, so each combination is built once.
        for i in range(start, len(ordered)):
            value = ordered[i]
            if value > remaining:
                break
            chosen.append(value)
            extend(i, remaining - value)
            chosen.pop()

    extend(0, target)
    return result
