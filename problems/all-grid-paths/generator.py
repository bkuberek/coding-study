"""Seeded inputs for all-grid-paths: the grid side is n, capped at the constraint of 10.

The answer has C(2n - 2, n - 1) strings (48,620 at n = 10), so the size of the output, not
the search, sets the cost. The input is a single integer, so the seed has no effect beyond
the size.
"""

import random

MIN_SIDE = 1
MAX_SIDE = 10


def generate(rng: random.Random, n: int) -> dict:
    return {"n": min(max(n, MIN_SIDE), MAX_SIDE)}


def validate(case_input: dict) -> None:
    assert MIN_SIDE <= case_input["n"] <= MAX_SIDE, "n out of range"
