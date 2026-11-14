"""Seeded inputs for maximal-square: grids of about n cells with blocks of ones.

The grid has between sqrt(n)/2 and sqrt(n) rows and about n / rows columns (at most 300
each), in a random orientation. Cells are ones with a density between 0.5 and 0.95, and on
most seeds a few solid blocks of ones are painted on top, so the best square is larger than
noise alone would give. Every approach visits each cell a constant number of times.
"""

import math
import random

MAX_SIDE = 300
MAX_BLOCKS = 3


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    side = math.isqrt(cells)
    rows = rng.randint(max(1, side // 2), max(1, side))
    columns = min(MAX_SIDE, max(1, cells // rows))
    if rng.random() < 0.5:
        rows, columns = columns, rows
    density = rng.uniform(0.5, 0.95)
    grid = [["1" if rng.random() < density else "0" for _ in range(columns)] for _ in range(rows)]
    for _ in range(rng.randint(0, MAX_BLOCKS)):
        size = rng.randint(1, min(rows, columns))
        top, left = rng.randint(0, rows - size), rng.randint(0, columns - size)
        for r in range(top, top + size):
            for c in range(left, left + size):
                grid[r][c] = "1"
    return {"matrix": grid}


def validate(case_input: dict) -> None:
    matrix = case_input["matrix"]
    assert 1 <= len(matrix) <= MAX_SIDE, "number of rows out of range"
    columns = len(matrix[0])
    assert 1 <= columns <= MAX_SIDE, "number of columns out of range"
    for row in matrix:
        assert len(row) == columns, "rows must have equal length"
        assert all(cell in ("0", "1") for cell in row), "cells must be '0' or '1'"
