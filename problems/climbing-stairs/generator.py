"""Seeded inputs for climbing-stairs.

The size is the number of steps itself, clamped to the constraint range 1..45 (the answer for
45 steps is the largest that fits in a 32-bit signed integer). Every input is fully determined
by `n`; `rng` is unused because there is nothing else to choose.
"""

import random

MIN_STEPS = 1
MAX_STEPS = 45


def generate(rng: random.Random, n: int) -> dict:
    return {"n": min(max(n, MIN_STEPS), MAX_STEPS)}


def validate(case_input: dict) -> None:
    assert MIN_STEPS <= case_input["n"] <= MAX_STEPS, "n out of range"
