"""Seeded inputs for sort-colors: random sequences of the colors 0, 1 and 2.

Each input draws its own color weights, and a weight can be zero, so some inputs lack one
or two colors entirely. That exercises the boundaries of every region: an empty block of
zeros, ones or twos must not shift the others.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
COLORS = (0, 1, 2)
WEIGHT_CHOICES = (0, 1, 2, 5)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    weights = [rng.choice(WEIGHT_CHOICES) for _ in COLORS]
    if not any(weights):
        weights[rng.randrange(len(COLORS))] = 1
    return {"nums": rng.choices(COLORS, weights=weights, k=length)}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(value in COLORS for value in nums), "colors must be 0, 1 or 2"
