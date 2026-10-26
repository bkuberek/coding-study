"""Seeded grids for shortest-path-binary-matrix.

`n` is the number of cells; the grid side is the largest `s` with `s * s <= n` (1 to 100).

Below SAWTOOTH_FROM cells the grid is random. Each cell is blocked with a probability between
0.1 and 0.35 per grid. On most grids a few walls are added on top, at least six rows apart,
each open at one end and with one gap, so shortest paths have to wind around them. The two
corners are opened on most grids and left to chance on the rest, so some answers are -1.

From SAWTOOTH_FROM cells on (the bench ladder), every grid is the same single corridor: bands
of two rows, separated by blocked rows, each crossed by a path that steps diagonally down
and up in turn, and joined at alternating ends; a last stretch runs down the right edge to
the end cell. The path holds about a third of the cells, and each step goes against the scan
order of one sweep direction, so the relaxation sweeps need one sweep per step: about n / 3
sweeps of n cells. The breadth-first search visits each open cell once.
"""

import math
import random

MAX_SIDE = 100
SAWTOOTH_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    side = min(MAX_SIDE, max(1, math.isqrt(max(n, 1))))
    if side * side >= SAWTOOTH_FROM:
        return {"grid": _sawtooth(side)}
    return {"grid": _random_grid(rng, side)}


def _sawtooth(side: int) -> list[list[int]]:
    grid = [[1] * side for _ in range(side)]
    # An odd number of bands, so the last one runs left to right and ends at the right edge.
    bands = (side + 1) // 3
    bands -= 1 - bands % 2
    for band in range(bands):
        top = 3 * band
        columns = range(side) if band % 2 == 0 else range(side - 1, -1, -1)
        for step, col in enumerate(columns):
            grid[top + step % 2][col] = 0
        end = columns[-1]
        # The band leaves from its lower row, through the blocked row below it.
        grid[top + 1][end] = 0
        for row in range(top + 2, min(top + 3, side)):
            grid[row][end] = 0
    for row in range(3 * bands - 1, side):
        grid[row][side - 1] = 0
    return grid


def _random_grid(rng: random.Random, side: int) -> list[list[int]]:
    blocked = rng.uniform(0.1, 0.35)
    grid = [[1 if rng.random() < blocked else 0 for _ in range(side)] for _ in range(side)]
    if side >= 5 and rng.random() < 0.7:
        candidates = range(2, side - 2, 6)
        walls = sorted(rng.sample(candidates, rng.randint(1, max(1, len(candidates) // 2))))
        for index, row in enumerate(walls):
            # Walls alternate the end they leave open and each has one gap in between;
            # the cells above and below the gap stay open so the gap can be used.
            span = range(0, side - 1) if index % 2 == 0 else range(1, side)
            gap = rng.randrange(side)
            for col in span:
                grid[row][col] = 0 if col == gap else 1
            grid[row - 1][gap] = grid[row + 1][gap] = 0
    if rng.random() < 0.85:
        grid[0][0] = grid[side - 1][side - 1] = 0
    return grid


def validate(case_input: dict) -> None:
    grid = case_input["grid"]
    side = len(grid)
    assert 1 <= side <= MAX_SIDE, "side out of range"
    assert all(len(row) == side for row in grid), "grid is not square"
    assert all(cell in (0, 1) for row in grid for cell in row), "cell is not 0 or 1"
