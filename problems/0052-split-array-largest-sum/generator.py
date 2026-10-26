"""Seeded inputs for split-array-largest-sum.

The array has n values drawn from [0, 10^6], with a few zeros and a few large values mixed
in. Once n reaches 10, k is between 5 and 10 (for smaller n, between max(1, n // 2) and n),
so the prefix dynamic program does about k * n^2 / 2 steps (quadratic in n at every seed),
while the binary search does n * log2(sum) steps.
"""

import random

MAX_LENGTH = 1000
MAX_VALUE = 10**6
MAX_PIECES = 50
GENERATED_MAX_PIECES = 10


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    nums = []
    for _ in range(length):
        roll = rng.random()
        if roll < 0.05:
            nums.append(0)
        elif roll < 0.10:
            nums.append(rng.randint(MAX_VALUE // 2, MAX_VALUE))
        else:
            nums.append(rng.randint(1, MAX_VALUE // 10))
    upper = min(length, GENERATED_MAX_PIECES)
    k = rng.randint(max(1, upper // 2), upper)
    return {"nums": nums, "k": k}


def validate(case_input: dict) -> None:
    nums, k = case_input["nums"], case_input["k"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value <= MAX_VALUE for value in nums), "value out of range"
    assert 1 <= k <= min(MAX_PIECES, len(nums)), "k out of range"
