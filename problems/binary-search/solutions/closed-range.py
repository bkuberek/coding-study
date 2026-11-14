def search(nums: list[int], target: int) -> int:
    # Invariant: if target is in nums, its index lies in [low, high].
    low, high = 0, len(nums) - 1
    while low <= high:
        middle = (low + high) // 2
        if nums[middle] == target:
            return middle
        if nums[middle] < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1
