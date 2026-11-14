"""Seeded inputs for first-last-position: a sorted array in which the target fills a long block.

The other values come from a pool of about n/3 distinct values, so they repeat as well.
The target is a value outside that pool and fills a block of between n/4 and n/2 positions,
so it is always present. A full scan reads all n elements, walking outwards from one found
occurrence takes between n/4 and n/2 steps (linear), and two bound searches take about
2 log2(n) probes. Absent targets and empty arrays are covered by the hand-written cases.
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    block = rng.randint(max(1, length // 4), max(1, length // 2))
    target = rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
    pool = [value for value in rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), max(2, length // 3) + 1) if value != target]
    others = rng.choices(pool, k=length - block)
    return {"nums": sorted(others + [target] * block), "target": target}


def validate(case_input: dict) -> None:
    nums, target = case_input["nums"], case_input["target"]
    assert len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert -VALUE_LIMIT <= target <= VALUE_LIMIT, "target out of range"
    assert all(left <= right for left, right in zip(nums, nums[1:])), "nums must not decrease"
