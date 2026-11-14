def search_range(nums: list[int], target: int) -> list[int]:
    low, high = 0, len(nums) - 1
    while low <= high:
        middle = (low + high) // 2
        if nums[middle] == target:
            first = last = middle
            while first > 0 and nums[first - 1] == target:
                first -= 1
            while last < len(nums) - 1 and nums[last + 1] == target:
                last += 1
            return [first, last]
        if nums[middle] < target:
            low = middle + 1
        else:
            high = middle - 1
    return [-1, -1]
