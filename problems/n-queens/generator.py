"""Seeded inputs for n-queens: the board size is n, capped at 8.

The constraint allows boards up to 10, but the scanning brute force explores tens of
thousands of partial boards at 10 and the oracle cross-check runs about 150 inputs at the
cap, so generated inputs stop at 8 (92 placements). Hand-written cases cover 9 and 10. The
input is a single integer, so the seed has no effect beyond the size.
"""

import random

MIN_SIZE = 1
MAX_GENERATED_SIZE = 8
MAX_SIZE = 10


def generate(rng: random.Random, n: int) -> dict:
    return {"n": min(max(n, MIN_SIZE), MAX_GENERATED_SIZE)}


def validate(case_input: dict) -> None:
    assert MIN_SIZE <= case_input["n"] <= MAX_SIZE, "n out of range"
