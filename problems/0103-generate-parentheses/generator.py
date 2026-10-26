"""Seeded inputs for generate-parentheses: the number of pairs is n, capped at 8.

The constraint allows 10 pairs, but the brute force writes C(2n, n) arrangements (184,756 at
n = 10) and the oracle cross-check runs about 150 inputs at the cap, so generated inputs
stop at 8 (12,870 arrangements, 1,430 answers). Hand-written cases cover 9 and 10. The input
is a single integer, so the seed has no effect beyond the size.
"""

import random

MIN_PAIRS = 1
MAX_GENERATED_PAIRS = 8
MAX_PAIRS = 10


def generate(rng: random.Random, n: int) -> dict:
    return {"n": min(max(n, MIN_PAIRS), MAX_GENERATED_PAIRS)}


def validate(case_input: dict) -> None:
    assert MIN_PAIRS <= case_input["n"] <= MAX_PAIRS, "n out of range"
