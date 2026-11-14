"""Seeded inputs for maximal-rectangle: grids with one side n and the other 3n/4 to n.

The grid has n rows and 3n/4 to n columns (at most 200 each), in a random orientation.
Most seeds are nearly all ones: each column holds about 1 to 4 zeros on average, so columns
of ones run far upwards and the walk up from every cell covers a constant share of the rows
above it. A fifth of the seeds use a 50% zero density for variety. The walk-up approach
then does about m^2 * n steps, cubic in the side length, while the histogram and boundary
approaches touch every cell a constant number of times.
"""

import random

MAX_SIDE = 200
DENSE_SHARE = 0.8
MIN_ZEROS_PER_COLUMN = 1
MAX_ZEROS_PER_COLUMN = 4
HALF = 0.5


def generate(rng: random.Random, n: int) -> dict:
    side = min(max(n, 1), MAX_SIDE)
    rows, columns = side, rng.randint(max(1, (3 * side) // 4), side)
    if rng.random() < DENSE_SHARE:
        zero_density = min(HALF, rng.uniform(MIN_ZEROS_PER_COLUMN, MAX_ZEROS_PER_COLUMN) / rows)
    else:
        zero_density = HALF
    if rng.random() < 0.5:
        rows, columns = columns, rows
    matrix = [["0" if rng.random() < zero_density else "1" for _ in range(columns)] for _ in range(rows)]
    return {"matrix": matrix}


def validate(case_input: dict) -> None:
    matrix = case_input["matrix"]
    assert 1 <= len(matrix) <= MAX_SIDE, "number of rows out of range"
    columns = len(matrix[0])
    assert 1 <= columns <= MAX_SIDE, "number of columns out of range"
    for row in matrix:
        assert len(row) == columns, "rows must have equal length"
        assert all(cell in ("0", "1") for cell in row), "cells must be '0' or '1'"
