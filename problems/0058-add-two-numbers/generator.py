"""Seeded inputs for add-two-numbers: two numbers as digit lists, least significant digit first.

The generator's size `n` is the digit count of the longer number, and which list is longer is
random. Below 100 digits, which covers the oracle's inputs, the other number has a uniformly
random length between 1 and `n`; from 100 digits on, the sizes the ladder times, it has n/2
digits, so converting both numbers costs the same share of n^2 at every seed. Most inputs use
random digits. A quarter of them use only nines, so a carry ripples through every digit and
the sum is one digit longer than the longer number. The most significant digit (the last node)
is never 0, except for the number 0 itself.
"""

import random

MIN_DIGITS = 1
MAX_DIGITS = 10**4
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    longer = min(max(n, MIN_DIGITS), MAX_DIGITS)
    shorter = longer // 2 if longer >= UNIFORM_FROM else rng.randint(MIN_DIGITS, longer)
    all_nines = rng.random() < 0.25
    first, second = _number(rng, longer, all_nines), _number(rng, shorter, all_nines)
    if rng.random() < 0.5:
        first, second = second, first
    return {"l1": first, "l2": second}


def _number(rng: random.Random, length: int, all_nines: bool) -> list[int]:
    if all_nines:
        return [9] * length
    if length == 1:
        return [rng.randint(0, 9)]
    return [rng.randint(0, 9) for _ in range(length - 1)] + [rng.randint(1, 9)]


def validate(case_input: dict) -> None:
    for digits in (case_input["l1"], case_input["l2"]):
        assert isinstance(digits, list), "a number must not be cyclic"
        assert MIN_DIGITS <= len(digits) <= MAX_DIGITS, "digit count out of range"
        assert all(0 <= digit <= 9 for digit in digits), "a node must hold one digit"
        assert len(digits) == 1 or digits[-1] != 0, "no leading zeros"
