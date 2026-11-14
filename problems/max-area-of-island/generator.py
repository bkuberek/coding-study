"""Seeded maps for max-area-of-island.

`n` is the number of cells. The map is roughly square (aspect ratio varies by seed, at most
300 by 300) and each cell is land with a probability drawn per map between 0.25 and 0.65,
so some maps hold many small islands and others one sprawling island near the percolation
threshold, which is where long winding flood fills happen. At n >= 90000 the map is the
full 300 by 300.
"""

import math
import random

MAX_SIDE = 300


def generate(rng: random.Random, n: int) -> dict:
    cells = max(n, 1)
    if cells >= MAX_SIDE * MAX_SIDE:
        rows = cols = MAX_SIDE
    else:
        rows = min(MAX_SIDE, max(1, round(math.sqrt(cells) * rng.uniform(0.5, 2.0))))
        cols = min(MAX_SIDE, max(1, cells // rows))
    land = rng.uniform(0.25, 0.65)
    grid = [[1 if rng.random() < land else 0 for _ in range(cols)] for _ in range(rows)]
    return {"grid": grid}


def validate(case_input: dict) -> None:
    grid = case_input["grid"]
    assert 1 <= len(grid) <= MAX_SIDE, "row count out of range"
    assert all(len(row) == len(grid[0]) for row in grid), "rows differ in length"
    assert 1 <= len(grid[0]) <= MAX_SIDE, "column count out of range"
    assert all(cell in (0, 1) for row in grid for cell in row), "cell is not 0 or 1"
