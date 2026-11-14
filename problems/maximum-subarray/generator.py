"""Seeded inputs for maximum-subarray.

`n` is the array length, clamped to 1..10^5, with values in -10^4..10^4. Each input picks one
shape: uniform values (best runs are short), values with a slight positive drift (long best
runs), or mostly negative values (the answer is often a single element or a short run).
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**4


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    shape = rng.choice(("uniform", "drift", "negative"))
    low, high = {
        "uniform": (-VALUE_LIMIT, VALUE_LIMIT),
        "drift": (-VALUE_LIMIT, VALUE_LIMIT + VALUE_LIMIT // 10),
        "negative": (-VALUE_LIMIT, VALUE_LIMIT // 5),
    }[shape]
    return {"nums": [min(VALUE_LIMIT, rng.randint(low, high)) for _ in range(length)]}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
