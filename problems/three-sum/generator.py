"""Seeded inputs for three-sum: values drawn from a range proportional to n.

Values are uniform in [-n, n], so duplicates are common (the deduplication logic is exercised
at every size) and the number of zero-sum triples grows roughly like n^2, as in the worst case
of the problem. The range is the same multiple of n at every seed, so the share of duplicates
and of zero-sum triples, which sets how much work the deduplication does, does not change from
one size of the ladder to the next. A few zeros are mixed in so the all-zero triple appears
often.
"""

import random

MIN_LENGTH = 3
MAX_LENGTH = 3000
VALUE_LIMIT = 10**5
RANGE_FACTOR = 1.0
ZERO_SHARE = 0.02


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    limit = min(VALUE_LIMIT, max(2, round(length * RANGE_FACTOR)))
    nums = [0 if rng.random() < ZERO_SHARE else rng.randint(-limit, limit) for _ in range(length)]
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
