"""Seeded inputs for find-peak-element: a long climb, then a jagged tail full of peaks.

The array rises strictly up to a position p between n/2 and n - 1 and then continues with
random values that differ from their neighbors, starting below the value at p. The first
peak is therefore p, so a scan for the first descent reads at least n/2 elements at every
seed (linear), while a binary search needs about log2(n) probes. The jagged tail usually
holds many other peaks, and a binary search may return any of them, which the checker
accepts. Values stay well inside the 32-bit range.
"""

import random

MAX_LENGTH = 10**5
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
MAX_STEP = 1000
TAIL_SPAN = 10**6


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    peak = rng.randint(length // 2, length - 1)
    value = rng.randint(-(2**30), 0)
    nums = [value]
    for _ in range(peak):
        value += rng.randint(1, MAX_STEP)
        nums.append(value)
    top = value
    previous = top
    for _ in range(length - peak - 1):
        candidate = rng.randint(top - TAIL_SPAN, top - 1)
        while candidate == previous:
            candidate = rng.randint(top - TAIL_SPAN, top - 1)
        nums.append(candidate)
        previous = candidate
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(INT_MIN <= value <= INT_MAX for value in nums), "value out of range"
    assert all(left != right for left, right in zip(nums, nums[1:])), "neighbors must differ"
