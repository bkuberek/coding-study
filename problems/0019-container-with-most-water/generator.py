"""Seeded inputs for container-with-most-water: bar heights in one of several shapes.

Shapes are random noise, rising, falling, a valley and a hill, so the best pair sits
sometimes at the ends, sometimes in the middle and sometimes close together. Every shape
keeps all heights within the constraints. Checking every pair costs n(n - 1)/2 steps for
every shape, and the two-pointer scan always costs n - 1 steps.
"""

import random

MIN_LENGTH = 2
MAX_LENGTH = 10**5
MAX_HEIGHT = 10**4
SHAPES = ("noise", "rising", "falling", "valley", "hill")


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    shape = rng.choice(SHAPES)
    height = [_bar(rng, shape, index, length) for index in range(length)]
    return {"height": height}


def validate(case_input: dict) -> None:
    height = case_input["height"]
    assert MIN_LENGTH <= len(height) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value <= MAX_HEIGHT for value in height), "height out of range"


def _bar(rng: random.Random, shape: str, index: int, length: int) -> int:
    position = index / (length - 1)
    if shape == "rising":
        base = position
    elif shape == "falling":
        base = 1 - position
    elif shape == "valley":
        base = abs(2 * position - 1)
    elif shape == "hill":
        base = 1 - abs(2 * position - 1)
    else:
        base = rng.random()
    jitter = rng.uniform(-0.1, 0.1)
    return min(MAX_HEIGHT, max(0, round((base + jitter) * MAX_HEIGHT)))
