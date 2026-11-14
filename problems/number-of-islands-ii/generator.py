"""Seeded inputs for number-of-islands-ii: a comb of land, then random cells.

There are n operations (capped at 10^4) on a grid about 2n / 3 columns wide and 2 to 4 rows
high (never more than 10^4 cells). A comb is a spine of land raised cell by cell along one
row, then teeth on every other cell of a neighboring row; it takes all n operations. From
COMB_FROM operations on (the bench ladder) every input is a comb. Below that, half of the
inputs are combs and the other half raise random cells, so repeated cells and merges of
several islands occur.

The comb is what slows naive union-find down: raising the spine cell by cell links each
old root under the new cell, which builds a chain as long as the spine, and every tooth
then runs a find from deep inside that chain, about k^2 / 4 steps in total. Recounting all
islands after each operation is quadratic as well; union by size with path compression
stays near-linear.
"""

import random

MIN_OPERATIONS = 1
MAX_OPERATIONS = 10**4
MAX_CELLS = 10**4
COMB_FROM = 100


def _comb(rng: random.Random, rows: int, cols: int) -> list[list[int]]:
    spine_row = rng.randrange(rows)
    tooth_row = spine_row + 1 if spine_row + 1 < rows else spine_row - 1
    order = list(range(cols))
    if rng.random() < 0.5:
        order.reverse()
    cells = [[spine_row, col] for col in order]
    if 0 <= tooth_row < rows:
        cells += [[tooth_row, col] for col in order[::2]]
    return cells


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_OPERATIONS), MAX_OPERATIONS)
    cols = max(1, (2 * count) // 3)
    rows = max(1, min(rng.randint(2, 4), MAX_CELLS // cols))
    comb = count >= COMB_FROM or rng.random() < 0.5
    positions = _comb(rng, rows, cols)[:count] if comb else []
    while len(positions) < count:
        positions.append([rng.randrange(rows), rng.randrange(cols)])
    if rng.random() < 0.5:
        rows, cols = cols, rows
        positions = [[col, row] for row, col in positions]
    return {"m": rows, "n": cols, "positions": positions}


def validate(case_input: dict) -> None:
    rows, cols, positions = case_input["m"], case_input["n"], case_input["positions"]
    assert 1 <= rows and 1 <= cols and rows * cols <= MAX_CELLS, "grid size out of range"
    assert MIN_OPERATIONS <= len(positions) <= MAX_OPERATIONS, "operation count out of range"
    assert all(len(cell) == 2 for cell in positions), "cells need a row and a column"
    assert all(0 <= row < rows and 0 <= col < cols for row, col in positions), "cell out of range"
