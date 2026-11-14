def search_insert(nums: list[int], target: int) -> int:
    low, high = 0, len(nums)  # the answer lies in [low, high]
    while low < high:
        middle = (low + high) // 2
        if nums[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low
