"""Seeded inputs for min-size-subarray-sum: targets that need long windows.

Values are positive and drawn from one of three ranges (tiny, mixed, full), and the
target is between 10% and 30% of the array's total, so the shortest valid window spans
a sizeable fraction of the array. Extending a window from every start then costs on the
order of n^2 / 10 steps at every seed. One input in ten gets a target above the total,
where the answer is 0 and every start scans to the end of the array.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
MAX_VALUE = 10**4
MAX_TARGET = 10**9
VALUE_RANGES = ((1, 10), (1, 1000), (1, MAX_VALUE))


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    low, high = rng.choice(VALUE_RANGES)
    nums = [rng.randint(low, high) for _ in range(length)]
    total = sum(nums)
    if rng.random() < 0.1 and total < MAX_TARGET:
        target = rng.randint(total + 1, min(MAX_TARGET, 2 * total))
    else:
        target = max(1, round(total * rng.uniform(0.1, 0.3)))
    return {"target": target, "nums": nums}


def validate(case_input: dict) -> None:
    target, nums = case_input["target"], case_input["nums"]
    assert 1 <= target <= MAX_TARGET, "target out of range"
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(1 <= value <= MAX_VALUE for value in nums), "value out of range"
