def search(nums: list[int], target: int) -> int:
    pivot = _index_of_minimum(nums)
    last = len(nums) - 1
    if nums[pivot] <= target <= nums[last]:
        return _binary_search(nums, target, pivot, last)
    return _binary_search(nums, target, 0, pivot - 1)


def _index_of_minimum(nums: list[int]) -> int:
    low, high = 0, len(nums) - 1
    while low < high:
        middle = (low + high) // 2
        if nums[middle] > nums[high]:
            low = middle + 1
        else:
            high = middle
    return low


def _binary_search(nums: list[int], target: int, low: int, high: int) -> int:
    while low <= high:
        middle = (low + high) // 2
        if nums[middle] == target:
            return middle
        if nums[middle] < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1
