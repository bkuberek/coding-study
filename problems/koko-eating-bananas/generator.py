"""Seeded inputs for koko-eating-bananas, built around a chosen speed.

The generator picks a speed `s` between n/20 and n/10 (between 1 and 30 for small n),
draws every pile between 1 and 50 * s bananas, and sets `h` to the hours those piles take at
speed `s`, plus a small slack. The answer is then at most `s` and, because piles are spread
over many multiples of `s`, very close to it. Trying speeds from 1 upward therefore does
about n^2/20 to n^2/10 pile divisions (quadratic at every seed), while a binary search over
[1, max(piles)] does n * log2(50 * s), that is n log n.
"""

import random

MAX_LENGTH = 10**4
MAX_PILE = 10**9
MAX_HOURS = 10**9
PILE_SPAN = 50


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    speed = rng.randint(max(1, length // 20), max(30, length // 10))
    piles = [rng.randint(1, PILE_SPAN * speed) for _ in range(length)]
    hours = sum((pile + speed - 1) // speed for pile in piles)
    slack = rng.randint(0, length // 4)
    return {"piles": piles, "h": min(hours + slack, MAX_HOURS)}


def validate(case_input: dict) -> None:
    piles, h = case_input["piles"], case_input["h"]
    assert 1 <= len(piles) <= MAX_LENGTH, "length out of range"
    assert all(1 <= pile <= MAX_PILE for pile in piles), "pile out of range"
    assert len(piles) <= h <= MAX_HOURS, "h out of range"
