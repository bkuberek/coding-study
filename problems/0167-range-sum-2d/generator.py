"""Seeded operation sequences for range-sum-2d.

`n` is the number of cells. The grid has about sqrt(n) rows (up to twice as many or half as
many, within the 200 x 200 limit) and n // rows columns, filled with uniform values. The
constructor is followed by n // 4 calls to `sumRegion` (at least one), each on a rectangle
with uniformly random corners, which covers about a ninth of the grid on average. Visiting
those cells costs O(n) per call and O(n^2) per sequence; prefix sums answer each call in O(1)
after an O(n) build.
"""

import math
import random

MAX_SIDE = 200
VALUE_LIMIT = 10**4
MAX_CALLS = 10**5
CALLS_PER_CELL = 4


def _corners(rng: random.Random, size: int) -> tuple[int, int]:
    first, second = rng.randrange(size), rng.randrange(size)
    return min(first, second), max(first, second)


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    rows = round(math.sqrt(cells) * 2 ** rng.uniform(-1, 1))
    rows = min(max(rows, math.ceil(cells / MAX_SIDE), 1), MAX_SIDE, cells)
    cols = min(max(cells // rows, 1), MAX_SIDE)
    matrix = [[rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(cols)] for _ in range(rows)]
    ops: list[str] = ["NumMatrix"]
    args: list[list] = [[matrix]]
    for _ in range(min(max(cells // CALLS_PER_CELL, 1), MAX_CALLS)):
        row1, row2 = _corners(rng, rows)
        col1, col2 = _corners(rng, cols)
        ops.append("sumRegion")
        args.append([row1, col1, row2, col2])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "NumMatrix" and len(args[0]) == 1, "the first op must be the constructor"
    matrix = args[0][0]
    assert 1 <= len(matrix) <= MAX_SIDE, "row count out of range"
    cols = len(matrix[0])
    assert 1 <= cols <= MAX_SIDE, "column count out of range"
    assert all(len(row) == cols for row in matrix), "rows differ in length"
    assert all(-VALUE_LIMIT <= v <= VALUE_LIMIT for row in matrix for v in row), "value out of range"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    for op, (row1, col1, row2, col2) in zip(ops[1:], args[1:], strict=True):
        assert op == "sumRegion", f"unknown op {op}"
        assert 0 <= row1 <= row2 < len(matrix), "rows out of bounds"
        assert 0 <= col1 <= col2 < cols, "columns out of bounds"
