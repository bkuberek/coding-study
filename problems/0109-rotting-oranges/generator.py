"""Seeded crates for rotting-oranges.

`n` is the number of cells. Below CHAIN_FROM cells the crate is random and roughly square
(aspect ratio varies by seed). Each cell is empty with a probability between 0.05 and 0.25 per
crate; the rest are oranges, and between 1 and about one orange in 400 starts rotten. About
one crate in four keeps oranges that are cut off by empty cells (answer -1); in the others
every fresh orange the rot cannot reach is removed, so the answer is the number of minutes the
rot needs.

From CHAIN_FROM cells on (the bench ladder), every crate is the worst case: a square crate
whose oranges form one winding chain, rows of oranges joined at alternating ends through
walls of empty cells, with a single rotten orange at one end. The rot needs about n / 2
minutes, so the per-minute rescan does about n^2 / 2 work on every seed, while the
breadth-first search handles each orange once.
"""

import math
import random
from collections import deque

MAX_SIDE = 100
CHAIN_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    cells = max(n, 1)
    if cells >= CHAIN_FROM:
        return {"grid": _winding_chain(rng, cells)}
    return {"grid": _random_crate(rng, cells)}


def _winding_chain(rng: random.Random, cells: int) -> list[list[int]]:
    side = min(MAX_SIDE, max(1, math.isqrt(cells)))
    grid = [[1 if r % 2 == 0 else 0 for _ in range(side)] for r in range(side)]
    for wall in range(1, side, 2):
        # Wall rows open at the right and the left end in turn.
        grid[wall][side - 1 if wall % 4 == 1 else 0] = 1
    grid[0][0] = 2
    if rng.random() < 0.5:
        grid = [list(column) for column in zip(*grid, strict=True)]
    return grid


def _random_crate(rng: random.Random, cells: int) -> list[list[int]]:
    rows = min(MAX_SIDE, max(1, round(math.sqrt(cells) * rng.uniform(0.6, 1.6))))
    cols = min(MAX_SIDE, max(1, cells // rows))
    empty = rng.uniform(0.05, 0.25)
    grid = [[0 if rng.random() < empty else 1 for _ in range(cols)] for _ in range(rows)]
    for _ in range(rng.randint(1, max(1, rows * cols // 400))):
        grid[rng.randrange(rows)][rng.randrange(cols)] = 2
    if rng.random() < 0.75:
        _remove_unreachable(grid)
    return grid


def _remove_unreachable(grid: list[list[int]]) -> None:
    rows, cols = len(grid), len(grid[0])
    reached = [[cell == 2 for cell in row] for row in grid]
    queue = deque((r, c) for r in range(rows) for c in range(cols) if grid[r][c] == 2)
    while queue:
        r, c = queue.popleft()
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1 and not reached[nr][nc]:
                reached[nr][nc] = True
                queue.append((nr, nc))
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1 and not reached[r][c]:
                grid[r][c] = 0


def validate(case_input: dict) -> None:
    grid = case_input["grid"]
    assert 1 <= len(grid) <= MAX_SIDE, "row count out of range"
    assert all(len(row) == len(grid[0]) for row in grid), "rows differ in length"
    assert 1 <= len(grid[0]) <= MAX_SIDE, "column count out of range"
    assert all(cell in (0, 1, 2) for row in grid for cell in row), "cell is not 0, 1 or 2"
