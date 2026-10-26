"""Seeded inputs for spiral-matrix: a matrix of about n cells with a random aspect ratio.

`n` is the number of cells. The row count is sqrt(n) scaled by a random factor between 1/4
and 4 (so thin and wide matrices both occur), kept within 1 to 300, and the column count is
n // rows, also within 1 to 300. Both approaches read every cell once, so both grow with n.
"""

import math
import random

MAX_SIDE = 300
VALUE_LIMIT = 1000


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    rows = round(math.sqrt(cells) * 4 ** rng.uniform(-1, 1))
    rows = min(max(rows, math.ceil(cells / MAX_SIDE), 1), MAX_SIDE, cells)
    cols = min(max(cells // rows, 1), MAX_SIDE)
    matrix = [[rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(cols)] for _ in range(rows)]
    return {"matrix": matrix}


def validate(case_input: dict) -> None:
    matrix = case_input["matrix"]
    assert 1 <= len(matrix) <= MAX_SIDE, "row count out of range"
    cols = len(matrix[0])
    assert 1 <= cols <= MAX_SIDE, "column count out of range"
    assert all(len(row) == cols for row in matrix), "rows differ in length"
    assert all(-VALUE_LIMIT <= v <= VALUE_LIMIT for row in matrix for v in row), "value out of range"
