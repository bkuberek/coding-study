"""Seeded inputs for max-ones-with-flips: random bits with a budget sized for long windows.

The share of ones is 30%, 50% or 80%. The budget k is chosen so that a window holding k
zeros spans between n/16 and n/8 positions on average: k = (share of zeros) * W for a
random W in that range. Extending a window from every start then costs about n * W
steps, quadratic at every seed. Budgets of 0 and of the full length are covered by the
hand-written cases.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
ONE_SHARES = (0.3, 0.5, 0.8)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    one_share = rng.choice(ONE_SHARES)
    nums = [1 if rng.random() < one_share else 0 for _ in range(length)]
    width = rng.randint(max(1, length // 16), max(1, length // 8))
    budget = min(length, round((1 - one_share) * width))
    return {"nums": nums, "k": budget}


def validate(case_input: dict) -> None:
    nums, budget = case_input["nums"], case_input["k"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(value in (0, 1) for value in nums), "values must be 0 or 1"
    assert 0 <= budget <= len(nums), "k out of range"
