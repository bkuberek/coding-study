"""Seeded inputs for largest-rectangle-histogram: bars with every kind of skyline.

Shapes are uniform heights, few distinct heights (long runs of equal bars), ascending and
descending staircases, a pyramid, and noise with zero-height gaps. The brute force always
extends every left bar to the end, n (n + 1) / 2 steps; the stack pushes and pops each bar
once, and its size reaches n on the ascending staircase.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
MAX_HEIGHT = 10**4
FEW_HEIGHTS = (0, 1, 2, 5, 10, 50)
ZERO_PROBABILITY = 0.05
SHAPES = ("uniform", "few", "ascending", "descending", "pyramid", "gaps")


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    shape = rng.choice(SHAPES)
    if shape == "few":
        heights = [rng.choice(FEW_HEIGHTS) for _ in range(length)]
    else:
        heights = [rng.randint(0, MAX_HEIGHT) for _ in range(length)]
    if shape == "ascending":
        heights.sort()
    elif shape == "descending":
        heights.sort(reverse=True)
    elif shape == "pyramid":
        heights.sort()
        heights = heights[0::2] + heights[1::2][::-1]
    elif shape == "gaps":
        heights = [0 if rng.random() < ZERO_PROBABILITY else height for height in heights]
    return {"heights": heights}


def validate(case_input: dict) -> None:
    heights = case_input["heights"]
    assert MIN_LENGTH <= len(heights) <= MAX_LENGTH, "length out of range"
    assert all(0 <= height <= MAX_HEIGHT for height in heights), "height out of range"
