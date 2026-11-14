"""Seeded inputs for multiply-strings: two random numbers of n and between n/2 and n digits.

`n` is the length of the longer factor; the shorter one has between n/2 and n digits, and
the order of the two is random. The leading digit is never 0. One input in twenty replaces a
factor of at most 30 digits by "0", so the zero product also shows up in the oracle
cross-check. Both approaches do a constant amount of work per pair of digits.
"""

import random

MAX_LENGTH = 2000
ZERO_SHARE = 0.05
SMALL_LENGTH = 30
DIGITS = "0123456789"


def _number(rng: random.Random, length: int) -> str:
    return rng.choice(DIGITS[1:]) + "".join(rng.choices(DIGITS, k=length - 1))


def generate(rng: random.Random, n: int) -> dict:
    longer = min(max(n, 1), MAX_LENGTH)
    shorter = rng.randint(max(longer // 2, 1), longer)
    first, second = _number(rng, longer), _number(rng, shorter)
    if longer <= SMALL_LENGTH and rng.random() < ZERO_SHARE:
        second = "0"
    if rng.random() < 0.5:
        first, second = second, first
    return {"num1": first, "num2": second}


def validate(case_input: dict) -> None:
    for name in ("num1", "num2"):
        number = case_input[name]
        assert 1 <= len(number) <= MAX_LENGTH, f"{name} length out of range"
        assert set(number) <= set(DIGITS), f"{name} has a non-digit"
        assert number == "0" or number[0] != "0", f"{name} has a leading zero"
