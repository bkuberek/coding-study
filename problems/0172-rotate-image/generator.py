"""Seeded inputs for rotate-image: an n x n matrix of uniform values.

`n` is the side length. Every approach touches each cell a constant number of times, so all
of them grow with n^2; they differ in extra memory.
"""

import random

MAX_SIDE = 500
VALUE_LIMIT = 1000


def generate(rng: random.Random, n: int) -> dict:
    side = min(max(n, 1), MAX_SIDE)
    matrix = [[rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(side)] for _ in range(side)]
    return {"matrix": matrix}


def validate(case_input: dict) -> None:
    matrix = case_input["matrix"]
    side = len(matrix)
    assert 1 <= side <= MAX_SIDE, "side out of range"
    assert all(len(row) == side for row in matrix), "the matrix must be square"
    assert all(-VALUE_LIMIT <= v <= VALUE_LIMIT for row in matrix for v in row), "value out of range"
