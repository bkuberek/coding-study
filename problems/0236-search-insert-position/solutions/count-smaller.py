def search_insert(nums: list[int], target: int) -> int:
    # In a sorted array, target belongs right after every smaller value.
    return sum(1 for value in nums if value < target)
