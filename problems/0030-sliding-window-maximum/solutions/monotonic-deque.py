from collections import deque


def max_sliding_window(nums: list[int], k: int) -> list[int]:
    candidates: deque[int] = deque()
    maxima = []
    for right, value in enumerate(nums):
        while candidates and nums[candidates[-1]] <= value:
            candidates.pop()
        candidates.append(right)
        if candidates[0] <= right - k:
            candidates.popleft()
        if right >= k - 1:
            maxima.append(nums[candidates[0]])
    return maxima
