def search(nums: list[int], target: int) -> int:
    for index, value in enumerate(nums):
        if value == target:
            return index
    return -1
