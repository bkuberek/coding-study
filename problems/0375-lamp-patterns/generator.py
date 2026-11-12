"""Seeded inputs for lamp-patterns: the number of lamps is n, capped at 14.

The input is a single integer, so the seed has no effect beyond the size. At the cap there are
987 allowed patterns, and the brute force writes all 16,384 strings of that length to find them.
"""

import random

MIN_LAMPS = 1
MAX_LAMPS = 14


def generate(rng: random.Random, n: int) -> dict:
    return {"n": min(max(n, MIN_LAMPS), MAX_LAMPS)}


def validate(case_input: dict) -> None:
    assert MIN_LAMPS <= case_input["n"] <= MAX_LAMPS, "n out of range"
