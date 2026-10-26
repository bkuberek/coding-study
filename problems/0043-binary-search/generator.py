"""Seeded inputs for binary-search: a strictly increasing array and a target.

The array holds `n` distinct values drawn from the whole value range and sorted. Half of
the seeds pick a target from the back half of the array, the other half pick a value that
is not in the array. A scan that compares every element with the target therefore reads at
least n/2 elements at every seed (linear), while a binary search needs about log2(n)
probes whether or not the target is present.
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    nums = sorted(rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), length))
    if rng.random() < 0.5:
        target = nums[rng.randint(length // 2, length - 1)]
    else:
        present = set(nums)
        target = rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
        while target in present:
            target = rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
    return {"nums": nums, "target": target}


def validate(case_input: dict) -> None:
    nums, target = case_input["nums"], case_input["target"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert -VALUE_LIMIT <= target <= VALUE_LIMIT, "target out of range"
    assert all(left < right for left, right in zip(nums, nums[1:])), "nums must be strictly increasing"
