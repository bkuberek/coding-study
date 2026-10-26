def combination_sum(candidates: list[int], target: int) -> list[list[int]]:
    result: list[list[int]] = []
    chosen: list[int] = []

    def explore(index: int, remaining: int) -> None:
        if remaining == 0:
            result.append(chosen.copy())
            return
        if remaining < 0 or index == len(candidates):
            return
        # Use candidates[index] once more and stay on it, since it may repeat.
        chosen.append(candidates[index])
        explore(index, remaining - candidates[index])
        chosen.pop()
        # Or never use it again.
        explore(index + 1, remaining)

    explore(0, target)
    return result
