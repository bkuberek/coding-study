def max_sliding_window(nums: list[int], k: int) -> list[int]:
    # Each max scans one window in C: still k steps per window.
    return [max(nums[start : start + k]) for start in range(len(nums) - k + 1)]
