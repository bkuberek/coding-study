def running_max(nums: list[int]) -> list[int]:
    result: list[int] = []
    best = nums[0]
    for value in nums:
        best = max(best, value)
        result.append(best)
    return result
