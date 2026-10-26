"""Seeded inputs for unique-paths: grids of about n cells with a random aspect ratio.

The grid has between sqrt(n)/2 and sqrt(n) rows and about n / rows columns (at most 1000
each), in a random orientation, so the table approaches visit about n cells and the
binomial approach multiplies about min(m, n) <= sqrt(n) factors.
"""

import math
import random

MAX_SIDE = 1000


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    side = math.isqrt(cells)
    rows = rng.randint(max(1, side // 2), max(1, side))
    columns = min(MAX_SIDE, max(1, cells // rows))
    if rng.random() < 0.5:
        rows, columns = columns, rows
    return {"m": rows, "n": columns}


def validate(case_input: dict) -> None:
    assert 1 <= case_input["m"] <= MAX_SIDE, "m out of range"
    assert 1 <= case_input["n"] <= MAX_SIDE, "n out of range"
