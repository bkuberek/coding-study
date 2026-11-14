def search(nums: list[int], target: int) -> int:
    # Find the first index whose value is >= target, in the half-open range [low, high).
    low, high = 0, len(nums)
    while low < high:
        middle = (low + high) // 2
        if nums[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low if low < len(nums) and nums[low] == target else -1
