"""Seeded inputs for move-zeroes: arrays in which about half of the values are zeros.

Each value is zero with probability 1/2, at random positions, so every approach does the
same work per element at every seed and the zeros give the branch no pattern to learn.
Small arrays still come out with no zeros, all zeros or anything between; the hand-written
cases pin those shapes down. Non-zero values span the whole 32-bit range, including
negatives, so a solution cannot rely on sign or magnitude to tell values apart.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
ZERO_SHARE = 0.5


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    nums = [0 if rng.random() < ZERO_SHARE else _non_zero(rng) for _ in range(length)]
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(INT_MIN <= value <= INT_MAX for value in nums), "value out of range"


def _non_zero(rng: random.Random) -> int:
    value = rng.randint(INT_MIN, INT_MAX - 1)
    return value if value < 0 else value + 1
