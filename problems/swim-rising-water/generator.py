"""Seeded pools for swim-rising-water.

`n` is the number of cells; the side is the largest `s` with `s * s <= n` (1 to 50). The
heights are a permutation of 0..s^2 - 1. Half of the pools are fully random; the other half
are ridged: a few full-width rows get the highest heights except at one gap cell each, so the
best route has to wind toward every gap, and the answer comes from deep inside the grid
rather than from the two corners.
"""

import math
import random

MAX_SIDE = 50


def generate(rng: random.Random, n: int) -> dict:
    side = min(MAX_SIDE, max(1, math.isqrt(max(n, 1))))
    cells = [(r, c) for r in range(side) for c in range(side)]
    rank = {cell: rng.random() for cell in cells}
    if side >= 4 and rng.random() < 0.5:
        for row in range(2, side - 1, rng.randint(2, 4)):
            gap = rng.randrange(side)
            for col in range(side):
                if col != gap:
                    rank[(row, col)] += 1.0  # ridge cells sort after every ordinary cell
    order = sorted(cells, key=lambda cell: (rank[cell], cell))
    grid = [[0] * side for _ in range(side)]
    for height, (r, c) in enumerate(order):
        grid[r][c] = height
    return {"grid": grid}


def validate(case_input: dict) -> None:
    grid = case_input["grid"]
    side = len(grid)
    assert 1 <= side <= MAX_SIDE, "side out of range"
    assert all(len(row) == side for row in grid), "grid is not square"
    assert sorted(value for row in grid for value in row) == list(range(side * side)), "heights are not a permutation"
