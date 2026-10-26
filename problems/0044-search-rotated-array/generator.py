"""Seeded inputs for search-rotated-array: a rotated increasing array of distinct values.

The generator sorts `n` distinct values, rotates them by a random amount between 0 and
n - 1, and then picks the target. Half of the seeds use the element at a random index in
the back half of the rotated array, the other half use a value that does not occur. A scan
from the left therefore reads at least n/2 elements at every seed (linear), while either
binary search needs about log2(n) probes.
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    ordered = sorted(rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), length))
    shift = rng.randrange(length)
    nums = ordered[shift:] + ordered[:shift]
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
    assert len(set(nums)) == len(nums), "values must be distinct"
    breaks = sum(1 for i in range(len(nums)) if nums[i] > nums[(i + 1) % len(nums)])
    assert breaks <= 1, "nums must be a rotated increasing array"
