def find_min(nums: list[int]) -> int:
    # Invariant: the index of the minimum lies in [low, high].
    low, high = 0, len(nums) - 1
    while low < high:
        middle = (low + high) // 2
        if nums[middle] > nums[high]:
            low = middle + 1
        else:
            high = middle
    return nums[low]
