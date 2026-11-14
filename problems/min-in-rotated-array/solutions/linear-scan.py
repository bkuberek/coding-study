def find_min(nums: list[int]) -> int:
    smallest = nums[0]
    for value in nums:
        if value < smallest:
            smallest = value
    return smallest
