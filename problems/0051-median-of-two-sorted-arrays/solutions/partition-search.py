import math


def find_median_sorted_arrays(nums1: list[int], nums2: list[int]) -> float:
    short, long = (nums1, nums2) if len(nums1) <= len(nums2) else (nums2, nums1)
    total = len(short) + len(long)
    lower_size = (total + 1) // 2
    low, high = 0, len(short)
    while low <= high:
        # Take `take_short` values from `short` and the rest of the lower half from `long`.
        take_short = (low + high) // 2
        take_long = lower_size - take_short
        short_left = short[take_short - 1] if take_short > 0 else -math.inf
        short_right = short[take_short] if take_short < len(short) else math.inf
        long_left = long[take_long - 1] if take_long > 0 else -math.inf
        long_right = long[take_long] if take_long < len(long) else math.inf
        if short_left > long_right:
            high = take_short - 1
        elif long_left > short_right:
            low = take_short + 1
        else:
            lower_max = max(short_left, long_left)
            if total % 2 == 1:
                return float(lower_max)
            return (lower_max + min(short_right, long_right)) / 2
    raise ValueError("the arrays must be sorted")
