def permute(nums: list[int]) -> list[list[int]]:
    result: list[list[int]] = []
    ordering: list[int] = []
    used = [False] * len(nums)

    def fill_next_slot() -> None:
        if len(ordering) == len(nums):
            result.append(ordering.copy())
            return
        for i, value in enumerate(nums):
            if used[i]:
                continue
            used[i] = True
            ordering.append(value)
            fill_next_slot()
            ordering.pop()
            used[i] = False

    fill_next_slot()
    return result
