"""Seeded inputs for count-set-bits: one unsigned 32-bit word.

The input is a single word, so `n` does not size anything. For n up to 32 (the range the
oracle cross-check uses) the number of set bits is drawn uniformly from 0 to 32, so every
popcount appears, including 0 and the full word. Above 32, every input has exactly 16 set
bits at random positions, the average for a uniform word, so all ladder sizes cost the
same: testing all 32 positions is constant work, and clearing the lowest set bit takes 16
steps.
"""

import random

WORD_BITS = 32
SMALL_SIZE = 32
LADDER_POPCOUNT = 16


def generate(rng: random.Random, n: int) -> dict:
    ones = rng.randint(0, WORD_BITS) if n <= SMALL_SIZE else LADDER_POPCOUNT
    value = sum(1 << bit for bit in rng.sample(range(WORD_BITS), ones))
    return {"n": value}


def validate(case_input: dict) -> None:
    assert 0 <= case_input["n"] < 2**WORD_BITS, "n must be an unsigned 32-bit value"
