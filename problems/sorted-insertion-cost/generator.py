"""Seeded inputs for sorted-insertion-cost: n values drawn uniformly from 1 to min(10^5, 4n).

With uniform values, the k-th insertion costs about k/4 on average, so the total is near
n^2/8: at n = 10^5 it is about 1.25 * 10^9, past the modulus 10^9 + 7. A sorted list with
binary search shifts about half the list on every insertion, which is quadratic but with
fast block moves; the Fenwick tree counts in log(max value) steps. At oracle sizes (30 or
fewer) the largest value is 3, 10 or 4n with equal probability, so repeated values are common.
"""

import random

MAX_LENGTH = 10**5
MAX_VALUE = 10**5
SMALL_UP_TO = 30
SPREAD = 4


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length <= SMALL_UP_TO:
        top = rng.choice((3, 10, SPREAD * length))
    else:
        top = min(MAX_VALUE, SPREAD * length)
    return {"instructions": [rng.randint(1, top) for _ in range(length)]}


def validate(case_input: dict) -> None:
    instructions = case_input["instructions"]
    assert 1 <= len(instructions) <= MAX_LENGTH, "length out of range"
    assert all(1 <= value <= MAX_VALUE for value in instructions), "value out of range"
