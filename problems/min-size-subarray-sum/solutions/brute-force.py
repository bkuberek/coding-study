def min_sub_array_len(target: int, nums: list[int]) -> int:
    best = 0
    for start in range(len(nums)):
        total = 0
        for end in range(start, len(nums)):
            total += nums[end]
            if total >= target:
                if best == 0 or end - start + 1 < best:
                    best = end - start + 1
                break
    return best
