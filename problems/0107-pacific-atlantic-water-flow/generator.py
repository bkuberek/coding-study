"""Seeded height maps for pacific-atlantic-water-flow.

`n` is the number of cells. Below BOWL_FROM cells the map is rolling terrain: a few random
hills and valleys on a tilted plane, plus noise, rounded to integers in 0..10^5 and coarsened
to a random step so that plateaus of equal height appear (water then reaches both oceans
through long flat routes). The aspect ratio varies by seed.

From BOWL_FROM cells on (the bench ladder), every map is the same nearly square bowl: each
ring of cells is flat, and the rings fall step by step from the border to the center. Water
from a cell k rings in runs over its whole ring and everything inside it, and never reaches
a coast, so the per-cell search visits about n^2 / 2 cells in total with no early exit; the
coast searches climb only the border ring, and the final scan keeps them linear.
"""

import math
import random

MAX_SIDE = 200
MAX_HEIGHT = 10**5
BOWL_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    cells = max(n, 1)
    if cells >= BOWL_FROM:
        return {"heights": _bowl(cells)}
    return {"heights": _terrain(rng, cells)}


def _bowl(cells: int) -> list[list[int]]:
    rows = min(MAX_SIDE, max(1, round(math.sqrt(cells))))
    cols = min(MAX_SIDE, max(1, cells // rows))
    deepest = (min(rows, cols) - 1) // 2
    ring_step = MAX_HEIGHT // (deepest + 1)
    return [
        [(deepest - min(r, c, rows - 1 - r, cols - 1 - c)) * ring_step for c in range(cols)]
        for r in range(rows)
    ]


def _terrain(rng: random.Random, cells: int) -> list[list[int]]:
    rows = min(MAX_SIDE, max(1, round(math.sqrt(cells) * rng.uniform(0.6, 1.6))))
    cols = min(MAX_SIDE, max(1, cells // rows))
    tilt_r, tilt_c = rng.uniform(-1, 1), rng.uniform(-1, 1)
    hills = [
        (rng.uniform(0, rows), rng.uniform(0, cols), rng.uniform(-3, 3), rng.uniform(1, max(rows, cols)))
        for _ in range(rng.randint(1, 4))
    ]
    raw = []
    for r in range(rows):
        line = []
        for c in range(cols):
            value = tilt_r * r / max(rows, 1) + tilt_c * c / max(cols, 1)
            for hr, hc, height, width in hills:
                value += height * math.exp(-((r - hr) ** 2 + (c - hc) ** 2) / (2 * width * width))
            line.append(value + rng.uniform(-0.3, 0.3))
        raw.append(line)
    low = min(min(line) for line in raw)
    high = max(max(line) for line in raw)
    span = (high - low) or 1.0
    step = rng.choice([1, 1000, 5000, 10000])
    return [
        [min(MAX_HEIGHT, int((value - low) / span * MAX_HEIGHT) // step * step) for value in line]
        for line in raw
    ]


def validate(case_input: dict) -> None:
    heights = case_input["heights"]
    assert 1 <= len(heights) <= MAX_SIDE, "row count out of range"
    assert all(len(row) == len(heights[0]) for row in heights), "rows differ in length"
    assert 1 <= len(heights[0]) <= MAX_SIDE, "column count out of range"
    assert all(0 <= value <= MAX_HEIGHT for row in heights for value in row), "height out of range"
