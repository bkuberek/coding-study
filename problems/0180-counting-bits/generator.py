"""Seeded inputs for counting-bits: the input is the size itself.

`n` is used as the input, so the output has n + 1 entries. The answer depends on nothing
else, so the generator draws no random values. Counting each number separately costs about
log2(n) / 2 steps per number, while the recurrence costs one step per number.
"""

import random

MAX_N = 10**6


def generate(rng: random.Random, n: int) -> dict:
    return {"n": min(max(n, 0), MAX_N)}


def validate(case_input: dict) -> None:
    assert 0 <= case_input["n"] <= MAX_N, "n out of range"
