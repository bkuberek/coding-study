"""Seeded inputs for contains-duplicate, shaped so every approach shows its declared growth.

About half of the inputs hold `n` distinct values (answer `false`). The others repeat one
value, and both copies sit in the last tenth of the array (answer `true`). Either way, a scan
over every pair compares about n^2/2 pairs before it can answer, and a one-pass hash set
reads at least nine tenths of the array before it stops.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
DUPLICATE_PROBABILITY = 0.5


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    nums = rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), length)
    if length >= 2 and rng.random() < DUPLICATE_PROBABILITY:
        tail = max(2, length // 10)
        later = rng.randrange(length - tail + 1, length)
        earlier = rng.randrange(length - tail, later)
        nums[later] = nums[earlier]
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
