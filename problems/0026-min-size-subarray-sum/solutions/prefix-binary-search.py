from bisect import bisect_left
from itertools import accumulate


def min_sub_array_len(target: int, nums: list[int]) -> int:
    prefix = [0, *accumulate(nums)]
    best = 0
    for start in range(len(nums)):
        end = bisect_left(prefix, prefix[start] + target, start + 1)
        if end < len(prefix) and (best == 0 or end - start < best):
            best = end - start
    return best
