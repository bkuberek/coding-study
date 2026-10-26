"""Seeded inputs for permutations: distinct values in [-10, 10].

The length is n, capped at the constraint of 6 values, so an answer never holds more than
6! = 720 orderings. Values are a random sample of the 21 allowed integers, in random order.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 6
VALUE_LIMIT = 10


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    return {"nums": rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), length)}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert len(set(nums)) == len(nums), "values must be distinct"
