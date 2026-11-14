"""Seeded inputs for min-in-rotated-array: a rotated increasing array of distinct values.

The generator sorts `n` distinct values from the whole value range and rotates them by a
random amount between 0 and n - 1. A scan for the smallest value reads all n elements at
every seed (linear); the binary search halves its range per step (logarithmic).
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    ordered = sorted(rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), length))
    shift = rng.randrange(length)
    return {"nums": ordered[shift:] + ordered[:shift]}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert len(set(nums)) == len(nums), "values must be distinct"
    breaks = sum(1 for i in range(len(nums)) if nums[i] > nums[(i + 1) % len(nums)])
    assert breaks <= 1, "nums must be a rotated increasing array"
