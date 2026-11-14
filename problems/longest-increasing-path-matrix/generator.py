"""Seeded inputs for longest-increasing-path-matrix: grids of about n cells.

The grid has between sqrt(n)/2 and sqrt(n) rows and about n / rows columns (at most 200
each), in a random orientation. Shapes are uniform values over the whole range (short
paths), values from 0 to 9 (many equal neighbors), and a gradient: a random direction
times a step plus noise smaller than the step, so increasing paths run across the grid and
reach about rows + columns cells, at most 399. Every shape keeps the longest path within
the 2000 cells the constraints promise. Every approach handles each cell and edge a constant
number of times, apart from the sort in sorted-cells.

From UNIFORM_FROM cells on (the bench ladder), every grid is square with uniform values, so
the cost per cell does not jump with the shape a seed happens to draw (the sort in particular
is much cheaper on the many ties of the small-values shape).
"""

import math
import random

MAX_SIDE = 200
INT_MAX = 2**31 - 1
MAX_PATH = 2000
SMALL_VALUES = 9
STEP = 1000
SHAPES = ("uniform", "small", "gradient")
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    side = math.isqrt(cells)
    if cells >= UNIFORM_FROM:
        return {"matrix": [[rng.randint(0, INT_MAX) for _ in range(side)] for _ in range(side)]}
    rows = rng.randint(max(1, side // 2), max(1, side))
    columns = min(MAX_SIDE, max(1, cells // rows))
    if rng.random() < 0.5:
        rows, columns = columns, rows
    shape = rng.choice(SHAPES)
    if shape == "uniform":
        matrix = [[rng.randint(0, INT_MAX) for _ in range(columns)] for _ in range(rows)]
    elif shape == "small":
        matrix = [[rng.randint(0, SMALL_VALUES) for _ in range(columns)] for _ in range(rows)]
    else:
        row_sign, column_sign = rng.choice((-1, 1)), rng.choice((-1, 1))
        base = STEP * (rows + columns)
        matrix = [
            [
                base + STEP * (row_sign * r + column_sign * c) + rng.randint(0, STEP - 1)
                for c in range(columns)
            ]
            for r in range(rows)
        ]
    return {"matrix": matrix}


def validate(case_input: dict) -> None:
    matrix = case_input["matrix"]
    assert 1 <= len(matrix) <= MAX_SIDE, "number of rows out of range"
    columns = len(matrix[0])
    assert 1 <= columns <= MAX_SIDE, "number of columns out of range"
    for row in matrix:
        assert len(row) == columns, "rows must have equal length"
        assert all(0 <= value <= INT_MAX for value in row), "value out of range"
    assert _longest_path(matrix) <= MAX_PATH, "the longest increasing path is too long"


def _longest_path(matrix: list[list[int]]) -> int:
    """Longest increasing path, by processing cells in decreasing order of value."""
    rows, columns = len(matrix), len(matrix[0])
    longest = [[1] * columns for _ in range(rows)]
    order = sorted(((matrix[r][c], r, c) for r in range(rows) for c in range(columns)), reverse=True)
    for value, r, c in order:
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < columns and matrix[nr][nc] > value:
                longest[r][c] = max(longest[r][c], 1 + longest[nr][nc])
    return max(max(row) for row in longest)
