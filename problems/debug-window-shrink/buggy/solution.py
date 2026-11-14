"""Debug: Window Shrink. Some tests fail: find the bug and fix it."""


def max_distinct_window_sum(nums: list[int], k: int) -> int:
    counts: dict[int, int] = {}
    window_sum = 0
    best = 0
    for right, value in enumerate(nums):
        counts[value] = counts.get(value, 0) + 1
        window_sum += value
        if right >= k:
            outgoing = nums[right - k]
            counts[outgoing] -= 1
            window_sum -= outgoing
        if right >= k - 1 and len(counts) == k:
            best = max(best, window_sum)
    return best
