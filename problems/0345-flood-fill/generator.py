"""Seeded inputs for flood-fill.

`n` is the number of cells (at most 50 by 50). From 100 cells on, the sizes the ladder times,
the grid has the same shape of input at every seed: about nine squares in ten have colour 0
and the rest are scattered over colours 1 to 3, the fill starts at the middle square (forced
to colour 0) and repaints with colour 5. That is far above the density at which same-coloured
squares stop forming one big connected region, so the fill reaches most of the grid every time.

Below 100 cells, which covers the oracle's inputs, the grids are small and varied: one to three
colours drawn per square, a random start, and a new colour from 0 to 4 that equals the old one
now and then (a fill that never stops on that input is the classic bug).
"""

import math
import random

MAX_SIDE = 50
COLOR_LIMIT = 10**4
BIG_FROM = 100
BACKGROUND = 0
BACKGROUND_SHARE = 0.9
NOISE_COLORS = (1, 2, 3)
BIG_NEW_COLOR = 5


def _shape(rng: random.Random, cells: int) -> tuple[int, int]:
    rows = min(MAX_SIDE, max(1, round(math.sqrt(cells) * rng.uniform(0.5, 2.0))))
    cols = min(MAX_SIDE, max(1, cells // rows))
    return rows, cols


def generate(rng: random.Random, n: int) -> dict:
    cells = min(max(n, 1), MAX_SIDE * MAX_SIDE)
    rows, cols = _shape(rng, cells)
    if cells >= BIG_FROM:
        grid = [
            [
                BACKGROUND if rng.random() < BACKGROUND_SHARE else rng.choice(NOISE_COLORS)
                for _ in range(cols)
            ]
            for _ in range(rows)
        ]
        row, col = rows // 2, cols // 2
        grid[row][col] = BACKGROUND
        return {"grid": grid, "row": row, "col": col, "newColor": BIG_NEW_COLOR}
    palette = rng.randint(1, 3)
    grid = [[rng.randrange(palette) for _ in range(cols)] for _ in range(rows)]
    return {
        "grid": grid,
        "row": rng.randrange(rows),
        "col": rng.randrange(cols),
        "newColor": rng.randint(0, 4),
    }


def validate(case_input: dict) -> None:
    grid, row, col = case_input["grid"], case_input["row"], case_input["col"]
    assert 1 <= len(grid) <= MAX_SIDE, "row count out of range"
    assert all(len(line) == len(grid[0]) for line in grid), "rows differ in length"
    assert 1 <= len(grid[0]) <= MAX_SIDE, "column count out of range"
    assert all(0 <= color <= COLOR_LIMIT for line in grid for color in line), "colour out of range"
    assert 0 <= row < len(grid) and 0 <= col < len(grid[0]), "start outside the grid"
    assert 0 <= case_input["newColor"] <= COLOR_LIMIT, "new colour out of range"
