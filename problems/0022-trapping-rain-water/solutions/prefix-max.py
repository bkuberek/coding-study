from itertools import accumulate


def trap(height: list[int]) -> int:
    left_max = list(accumulate(height, max))
    right_max = list(accumulate(reversed(height), max))[::-1]
    return sum(min(left, right) - bar for left, right, bar in zip(left_max, right_max, height))
