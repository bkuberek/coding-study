def check_subarray_sum(nums: list[int], k: int) -> bool:
    for start in range(len(nums)):
        total = nums[start]
        for end in range(start + 1, len(nums)):
            total += nums[end]
            if total % k == 0:
                return True
    return False
