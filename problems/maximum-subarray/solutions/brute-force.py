def max_sub_array(nums: list[int]) -> int:
    best = nums[0]
    for start in range(len(nums)):
        total = 0
        for end in range(start, len(nums)):
            total += nums[end]
            best = max(best, total)
    return best
