"""Seeded inputs for phone-letter-combinations: random keys from 2 to 9.

The length is n, capped at the constraint of 6 keys, so an answer holds at most
4^6 = 4096 words (six presses of 7 or 9). The empty input is covered by a hand-written case.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 6
KEYS = "23456789"


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    return {"digits": "".join(rng.choice(KEYS) for _ in range(length))}


def validate(case_input: dict) -> None:
    digits = case_input["digits"]
    assert len(digits) <= MAX_LENGTH, "too many digits"
    assert set(digits) <= set(KEYS), "digits must be between 2 and 9"
