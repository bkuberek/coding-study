"""Seeded grids for min-obstacle-removal.

`n` is the number of cells (2 to 10^5); the grid is roughly square, with the aspect ratio
varying by seed (at most 10^5 cells and at least 2). Each cell is an obstacle with a
probability between 0.2 and 0.7, so answers range from 0 on open grids to dozens on crowded
ones. On some grids, full-width walls with a single gap are added, so a route either detours
to the gap or pays a removal to cut through. Both corners are empty.
"""

import math
import random

MAX_CELLS = 10**5


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 2), MAX_CELLS)
    rows = max(1, min(cells, round(math.sqrt(cells) * rng.uniform(0.5, 2.0))))
    cols = max(1, cells // rows)
    if rows * cols < 2:
        cols = 2
    density = rng.uniform(0.2, 0.7)
    grid = [[1 if rng.random() < density else 0 for _ in range(cols)] for _ in range(rows)]
    if rows >= 3 and rng.random() < 0.4:
        row = rng.randint(1, min(3, rows - 2))
        while row < rows - 1:
            gap = rng.randrange(cols)
            for col in range(cols):
                grid[row][col] = 0 if col == gap else 1
            row += rng.randint(3, 8)
    grid[0][0] = grid[rows - 1][cols - 1] = 0
    return {"grid": grid}


def validate(case_input: dict) -> None:
    grid = case_input["grid"]
    rows = len(grid)
    assert rows >= 1 and all(len(row) == len(grid[0]) for row in grid), "grid is not rectangular"
    cols = len(grid[0])
    assert 2 <= rows * cols <= MAX_CELLS, "cell count out of range"
    assert all(cell in (0, 1) for row in grid for cell in row), "cell is not 0 or 1"
    assert grid[0][0] == 0 and grid[rows - 1][cols - 1] == 0, "a corner is an obstacle"
