def search_range(nums: list[int], target: int) -> list[int]:
    first = last = -1
    for index, value in enumerate(nums):
        if value == target:
            if first == -1:
                first = index
            last = index
    return [first, last]
