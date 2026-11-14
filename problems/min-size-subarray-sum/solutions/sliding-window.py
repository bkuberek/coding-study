def min_sub_array_len(target: int, nums: list[int]) -> int:
    best = 0
    total = 0
    left = 0
    for right, value in enumerate(nums):
        total += value
        while total >= target:
            if best == 0 or right - left + 1 < best:
                best = right - left + 1
            total -= nums[left]
            left += 1
    return best
