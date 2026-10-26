"""Seeded inputs for search-2d-matrix: a grid of about n cells in row-major sorted order.

The grid has between sqrt(n)/2 and sqrt(n) rows and enough columns to stay within n cells.
Its values are distinct sorted samples laid out row by row; then a few cells copy their left
neighbor, so rows may repeat values while each row's first value stays above the previous
row's last. Half of the seeds look for a value that is present, the other half for a value
that is absent.

Below 100 cells, which covers the oracle's inputs, a present target comes from anywhere in
the back half of the cells in row-major order and an absent one from anywhere in the range.
From 100 cells on, the sizes the ladder times, both sit at the same place relative to the
grid: the cell three quarters down and a quarter across, or the gap just after it. A full
scan then reads at least three quarters of the cells (linear in n) and the staircase walk
takes about three quarters of rows + columns steps (about sqrt(n)) at every seed, instead of
a number of steps that depends on where a random target falls; the binary search needs about
log2(n) probes.
"""

import itertools
import math
import random

MAX_CELLS = 10**5
VALUE_LIMIT = 10**9
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_CELLS)
    side = math.isqrt(cells)
    rows = rng.randint(max(1, side // 2), max(1, side))
    columns = max(1, cells // rows)
    values = sorted(rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), rows * columns))
    matrix = [values[row * columns:(row + 1) * columns] for row in range(rows)]
    for _ in range(rows * columns // 10):
        row, column = rng.randrange(rows), rng.randrange(columns)
        if column > 0:
            matrix[row][column] = matrix[row][column - 1]
    present = rng.random() < 0.5
    if rows * columns >= UNIFORM_FROM:
        target = _anchored_target(rng, matrix, present)
    elif present:
        position = rng.randint(rows * columns // 2, rows * columns - 1)
        target = matrix[position // columns][position % columns]
    else:
        target = _absent_value(rng, matrix)
    return {"matrix": matrix, "target": target}


def _anchored_target(rng: random.Random, matrix: list[list[int]], present: bool) -> int:
    """The value three quarters down and a quarter across, or one in the first gap after it."""
    rows, columns = len(matrix), len(matrix[0])
    anchor = (3 * rows // 4) * columns + columns // 4
    flat = [value for row in matrix for value in row]
    if present:
        return flat[anchor]
    for value, following in itertools.pairwise(flat[anchor:]):
        if following - value >= 2:
            return value + 1
    return _absent_value(rng, matrix)


def _absent_value(rng: random.Random, matrix: list[list[int]]) -> int:
    present = {value for row in matrix for value in row}
    target = rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
    while target in present:
        target = rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
    return target


def validate(case_input: dict) -> None:
    matrix, target = case_input["matrix"], case_input["target"]
    assert len(matrix) >= 1 and len(matrix[0]) >= 1, "the grid must not be empty"
    columns = len(matrix[0])
    assert all(len(row) == columns for row in matrix), "rows must have equal length"
    assert len(matrix) * columns <= MAX_CELLS, "too many cells"
    assert -VALUE_LIMIT <= target <= VALUE_LIMIT, "target out of range"
    for row in matrix:
        assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in row), "value out of range"
        assert all(left <= right for left, right in zip(row, row[1:])), "rows must not decrease"
    for upper, lower in zip(matrix, matrix[1:]):
        assert upper[-1] < lower[0], "each row must start above the previous row's end"
