def combination_sum2(candidates: list[int], target: int) -> list[list[int]]:
    ordered = sorted(candidates)
    result: list[list[int]] = []
    chosen: list[int] = []

    def extend(start: int, remaining: int) -> None:
        if remaining == 0:
            result.append(chosen.copy())
            return
        for i in range(start, len(ordered)):
            value = ordered[i]
            if value > remaining:
                break
            # A second copy at the same level would rebuild the first copy's combinations.
            if i > start and value == ordered[i - 1]:
                continue
            chosen.append(value)
            extend(i + 1, remaining - value)
            chosen.pop()

    extend(0, target)
    return result
