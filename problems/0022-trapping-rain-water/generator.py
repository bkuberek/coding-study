"""Seeded inputs for trapping-rain-water: terrains with basins at every scale.

Shapes are random noise (many small puddles), a random walk (wide uneven basins), one
large valley, and a ridge of a few tall peaks over low noise. Heights stay within the
constraints. Scanning both sides of every bar costs about n^2 steps for every shape; the
linear approaches touch each bar a constant number of times.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
MAX_HEIGHT = 10**4
SHAPES = ("noise", "walk", "valley", "peaks")


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    shape = rng.choice(SHAPES)
    if shape == "walk":
        height = _walk(rng, length)
    elif shape == "valley":
        height = [_clamp(abs(2 * i / max(1, length - 1) - 1) * MAX_HEIGHT + rng.randint(-500, 500)) for i in range(length)]
    elif shape == "peaks":
        height = _peaks(rng, length)
    else:
        height = [rng.randint(0, MAX_HEIGHT) for _ in range(length)]
    return {"height": height}


def validate(case_input: dict) -> None:
    height = case_input["height"]
    assert MIN_LENGTH <= len(height) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value <= MAX_HEIGHT for value in height), "height out of range"


def _walk(rng: random.Random, length: int) -> list[int]:
    level = rng.randint(0, MAX_HEIGHT)
    height = []
    for _ in range(length):
        level = _clamp(level + rng.randint(-300, 300))
        height.append(level)
    return height


def _peaks(rng: random.Random, length: int) -> list[int]:
    height = [rng.randint(0, MAX_HEIGHT // 10) for _ in range(length)]
    for _ in range(rng.randint(1, 5)):
        height[rng.randrange(length)] = rng.randint(MAX_HEIGHT // 2, MAX_HEIGHT)
    return height


def _clamp(value: float) -> int:
    return min(MAX_HEIGHT, max(0, round(value)))
