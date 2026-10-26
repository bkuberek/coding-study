from collections import Counter


def single_number(nums: list[int]) -> int:
    counts = Counter(nums)
    return next(value for value, count in counts.items() if count == 1)
