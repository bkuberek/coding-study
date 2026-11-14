"""Seeded inputs for fruit-into-baskets: overlapping stretches of two fruit types.

The row is a chain of segments between n/8 and n/4 trees long. Each segment mixes two
types, and consecutive segments share one type, so the best window usually straddles a
boundary and runs back to the start of the shared type's last run. Up to three trees get
a random type that breaks a stretch at an unpredictable place.

Walking from every starting tree then covers about a segment per start, on the order of
n^2 / 6 steps at every seed, while the sliding windows stay linear.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
MAX_NOISE_TREES = 3


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    fruits: list[int] = []
    shared, other = rng.randrange(length), rng.randrange(length)
    while len(fruits) < length:
        size = rng.randint(max(1, length // 8), max(1, length // 4))
        fruits.extend(shared if rng.random() < 0.5 else other for _ in range(size))
        shared, other = fruits[-1], rng.randrange(length)
    fruits = fruits[:length]
    for _ in range(rng.randint(0, MAX_NOISE_TREES)):
        fruits[rng.randrange(length)] = rng.randrange(length)
    return {"fruits": fruits}


def validate(case_input: dict) -> None:
    fruits = case_input["fruits"]
    assert MIN_LENGTH <= len(fruits) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value < len(fruits) for value in fruits), "fruit type out of range"
