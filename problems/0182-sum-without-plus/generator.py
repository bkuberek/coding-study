"""Seeded inputs for sum-without-plus: two 32-bit signed integers whose sum fits in 32 bits.

The inputs are two words, so `n` does not size anything. `a` is drawn from a range picked per
input (small values near 0, or the whole 32-bit range), and `b` uniformly from the values
that keep `a + b` inside the 32-bit range. Mixed signs, carries across the sign bit and long
carry chains all occur. Both approaches do at most 32 rounds per call.
"""

import random

INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
SMALL_LIMIT = 1000


def generate(rng: random.Random, n: int) -> dict:
    limit = SMALL_LIMIT if rng.random() < 0.25 else INT_MAX
    a = rng.randint(max(-limit, INT_MIN), limit)
    b = rng.randint(max(INT_MIN - a, INT_MIN), min(INT_MAX - a, INT_MAX))
    return {"a": a, "b": b}


def validate(case_input: dict) -> None:
    a, b = case_input["a"], case_input["b"]
    assert INT_MIN <= a <= INT_MAX and INT_MIN <= b <= INT_MAX, "operand out of range"
    assert INT_MIN <= a + b <= INT_MAX, "the sum must fit in 32 bits"
