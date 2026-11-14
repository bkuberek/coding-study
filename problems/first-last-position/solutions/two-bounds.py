def search_range(nums: list[int], target: int) -> list[int]:
    first = _first_index(nums, lambda value: value >= target)
    if first == len(nums) or nums[first] != target:
        return [-1, -1]
    return [first, _first_index(nums, lambda value: value > target) - 1]


def _first_index(nums: list[int], is_past) -> int:
    # The smallest index whose value satisfies the monotone predicate, or len(nums).
    low, high = 0, len(nums)
    while low < high:
        middle = (low + high) // 2
        if is_past(nums[middle]):
            high = middle
        else:
            low = middle + 1
    return low
