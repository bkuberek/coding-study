def subsets(nums: list[int]) -> list[list[int]]:
    result: list[list[int]] = []
    chosen: list[int] = []

    def explore(index: int) -> None:
        if index == len(nums):
            result.append(chosen.copy())
            return
        chosen.append(nums[index])
        explore(index + 1)
        chosen.pop()
        explore(index + 1)

    explore(0)
    return result
