"""Seeded inputs for burst-balloons: n balloons with values from 0 to 100.

Values are uniform over [0, 100] on half of the seeds; on the other half they come from a
narrow random band, so many balloons are equal, and about one in ten is set to 0. Every
approach evaluates all O(n^3) (interval, last balloon) pairs whatever the values are, so
the shape only changes the answer, not the work.
"""

import random

MAX_LENGTH = 300
MAX_VALUE = 100
BAND = 10
ZERO_PROBABILITY = 0.1


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if rng.random() < 0.5:
        nums = [rng.randint(0, MAX_VALUE) for _ in range(length)]
    else:
        low = rng.randint(0, MAX_VALUE - BAND)
        nums = [
            0 if rng.random() < ZERO_PROBABILITY else rng.randint(low, low + BAND)
            for _ in range(length)
        ]
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value <= MAX_VALUE for value in nums), "value out of range"
