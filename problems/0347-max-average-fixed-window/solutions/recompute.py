def max_window_average(nums: list[int], k: int) -> float:
    # One window starts at each position that leaves room for k numbers.
    return max(sum(nums[start : start + k]) / k for start in range(len(nums) - k + 1))
