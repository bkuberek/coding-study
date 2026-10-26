"""Seeded grids for shortest-path-with-removals.

`n` is the number of cells; the grid is roughly square (aspect ratio varies by seed, at most
40 by 40). Each cell is an obstacle with a probability between 0.05 and 0.35 per grid. On most
grids, full-width walls with a single gap cross the grid every 4 to 8 rows, so a route either
detours to each gap or spends removals to cut through. Both corners are empty. Usually `k` is
between 0 and min(10, (m + n) / 4), so the state space of about m·n·(k + 1) grows linearly
with the grid; on one input in ten `k` is large (up to m·n), where the bound m + n - 3 caps
the useful removals.

From UNIFORM_FROM cells on (the bench ladder), every grid has one shape: square, obstacle
density 0.2, a wall every WALL_SPACING rows, and k = LADDER_K. The state space then grows
linearly with the grid on every seed, instead of jumping with a random k, and no seed takes
the shortcut that a k of at least m + n - 3 allows.
"""

import math
import random

MAX_SIDE = 40
SMALL_K = 10
UNIFORM_FROM = 100
LADDER_DENSITY = 0.2
WALL_SPACING = 6
LADDER_K = 5


def generate(rng: random.Random, n: int) -> dict:
    cells = max(n, 1)
    if cells >= UNIFORM_FROM:
        return _uniform(rng, cells)
    if cells >= MAX_SIDE * MAX_SIDE:
        rows = cols = MAX_SIDE
    else:
        rows = min(MAX_SIDE, max(1, round(math.sqrt(cells) * rng.uniform(0.6, 1.6))))
        cols = min(MAX_SIDE, max(1, cells // rows))
    density = rng.uniform(0.05, 0.35)
    grid = [[1 if rng.random() < density else 0 for _ in range(cols)] for _ in range(rows)]
    if rows >= 3 and rng.random() < 0.7:
        # Full-width walls with one gap each: a route either detours to the gap or spends
        # removals to cut through, which is the trade-off the search has to weigh.
        row = rng.randint(1, min(3, rows - 2))
        while row < rows - 1:
            gap = rng.randrange(cols)
            for col in range(cols):
                grid[row][col] = 0 if col == gap else 1
            row += rng.randint(4, 8)
    grid[0][0] = grid[rows - 1][cols - 1] = 0
    if rng.random() < 0.1:
        k = rng.randint(0, rows * cols)
    else:
        k = rng.randint(0, min(SMALL_K, max(1, (rows + cols) // 4)))
    return {"grid": grid, "k": k}


def _uniform(rng: random.Random, cells: int) -> dict:
    side = min(MAX_SIDE, math.isqrt(cells))
    grid = [[1 if rng.random() < LADDER_DENSITY else 0 for _ in range(side)] for _ in range(side)]
    for row in range(WALL_SPACING // 2, side - 1, WALL_SPACING):
        gap = rng.randrange(side)
        for col in range(side):
            grid[row][col] = 0 if col == gap else 1
    grid[0][0] = grid[side - 1][side - 1] = 0
    return {"grid": grid, "k": LADDER_K}


def validate(case_input: dict) -> None:
    grid, k = case_input["grid"], case_input["k"]
    rows = len(grid)
    assert 1 <= rows <= MAX_SIDE, "row count out of range"
    assert all(len(row) == len(grid[0]) for row in grid), "rows differ in length"
    cols = len(grid[0])
    assert 1 <= cols <= MAX_SIDE, "column count out of range"
    assert all(cell in (0, 1) for row in grid for cell in row), "cell is not 0 or 1"
    assert grid[0][0] == 0 and grid[rows - 1][cols - 1] == 0, "a corner is an obstacle"
    assert 0 <= k <= rows * cols, "k out of range"
