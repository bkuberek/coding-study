"""Seeded inputs for house-robber.

`n` is the number of houses, clamped to 1..2000. Each input picks one value shape so that both
simple alternation and irregular choices are needed: uniform cash, mostly small cash with rare
large houses (where skipping two in a row pays), or runs of equal cash.
"""

import random

MIN_HOUSES = 1
MAX_HOUSES = 2000
MAX_CASH = 10**4
RUN_LENGTH_LIMIT = 5


def generate(rng: random.Random, n: int) -> dict:
    houses = min(max(n, MIN_HOUSES), MAX_HOUSES)
    shape = rng.choice(("uniform", "spikes", "runs"))
    if shape == "uniform":
        nums = [rng.randint(0, MAX_CASH) for _ in range(houses)]
    elif shape == "spikes":
        nums = [
            rng.randint(MAX_CASH // 2, MAX_CASH) if rng.random() < 0.1 else rng.randint(0, 100)
            for _ in range(houses)
        ]
    else:
        nums = []
        while len(nums) < houses:
            nums += [rng.randint(0, MAX_CASH)] * rng.randint(1, RUN_LENGTH_LIMIT)
        nums = nums[:houses]
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_HOUSES <= len(nums) <= MAX_HOUSES, "length out of range"
    assert all(0 <= cash <= MAX_CASH for cash in nums), "cash out of range"
