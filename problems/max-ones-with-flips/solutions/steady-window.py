def longest_ones(nums: list[int], k: int) -> int:
    left = 0
    flips_left = k
    for value in nums:
        if value == 0:
            flips_left -= 1
        if flips_left < 0:
            if nums[left] == 0:
                flips_left += 1
            left += 1
    return len(nums) - left
