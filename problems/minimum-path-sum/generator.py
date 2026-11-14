"""Seeded inputs for minimum-path-sum: grids of about n cells with a random aspect ratio.

The grid has between sqrt(n) / 2 and sqrt(n) rows and about n / rows columns (at most 200
each), in a random orientation, so both approaches visit about n cells. Tolls are uniform
between 0 and 100.
"""

import math
import random

MAX_SIDE = 200
MAX_TOLL = 100


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    side = math.isqrt(cells)
    rows = rng.randint(max(1, side // 2), max(1, side))
    columns = min(MAX_SIDE, max(1, cells // rows))
    if rng.random() < 0.5:
        rows, columns = columns, rows
    grid = [[rng.randint(0, MAX_TOLL) for _ in range(columns)] for _ in range(rows)]
    return {"grid": grid}


def validate(case_input: dict) -> None:
    grid = case_input["grid"]
    assert 1 <= len(grid) <= MAX_SIDE, "row count out of range"
    assert 1 <= len(grid[0]) <= MAX_SIDE, "column count out of range"
    assert all(len(row) == len(grid[0]) for row in grid), "rows must have equal length"
    assert all(0 <= toll <= MAX_TOLL for row in grid for toll in row), "toll out of range"
