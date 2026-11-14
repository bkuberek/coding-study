"""Seeded inputs for set-matrix-zeroes: a matrix of about n cells with a few zeros.

`n` is the number of cells. The shape follows spiral-matrix: sqrt(n) rows scaled by a random
factor between 1/4 and 4, within 1 to 300 per side. Values are uniform non-zero 32-bit
integers. Between 0 and about sqrt(n) / 2 cells are then set to 0 (sometimes none, sometimes
in the first row or column), so most rows and columns survive and the output is not all
zeros. Both approaches scan the matrix a constant number of times.
"""

import math
import random

MAX_SIDE = 300
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1


def _nonzero(rng: random.Random) -> int:
    value = rng.randint(INT_MIN, INT_MAX - 1)
    return value + 1 if value >= 0 else value


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    rows = round(math.sqrt(cells) * 4 ** rng.uniform(-1, 1))
    rows = min(max(rows, math.ceil(cells / MAX_SIDE), 1), MAX_SIDE, cells)
    cols = min(max(cells // rows, 1), MAX_SIDE)
    matrix = [[_nonzero(rng) for _ in range(cols)] for _ in range(rows)]
    for _ in range(rng.randint(0, max(math.isqrt(rows * cols) // 2, 1))):
        matrix[rng.randrange(rows)][rng.randrange(cols)] = 0
    return {"matrix": matrix}


def validate(case_input: dict) -> None:
    matrix = case_input["matrix"]
    assert 1 <= len(matrix) <= MAX_SIDE, "row count out of range"
    cols = len(matrix[0])
    assert 1 <= cols <= MAX_SIDE, "column count out of range"
    assert all(len(row) == cols for row in matrix), "rows differ in length"
    assert all(INT_MIN <= v <= INT_MAX for row in matrix for v in row), "value out of range"
