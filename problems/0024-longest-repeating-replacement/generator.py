"""Seeded inputs for longest-repeating-replacement: mildly skewed letter mixes.

Each input draws letters from 3, 5 or 26 uppercase letters with weights from 1 to 3, so
one letter is somewhat more common than the rest but never dominates, and sets k between
n/16 and n/8. Valid windows are then a few times k long: extending a window from every
start costs on the order of n * k steps, which keeps the brute force quadratic at every
seed while it still finishes in about a second at the largest ladder size. Budgets of 0
and of the full length are covered by the hand-written cases.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**5
LETTER_COUNTS = (3, 5, 26)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    letters = rng.sample(string.ascii_uppercase, rng.choice(LETTER_COUNTS))
    weights = [rng.randint(1, 3) for _ in letters]
    text = "".join(rng.choices(letters, weights=weights, k=length))
    budget = rng.randint(length // 16, length // 8)
    return {"s": text, "k": budget}


def validate(case_input: dict) -> None:
    text, budget = case_input["s"], case_input["k"]
    assert MIN_LENGTH <= len(text) <= MAX_LENGTH, "length out of range"
    assert all("A" <= ch <= "Z" for ch in text), "only uppercase letters are allowed"
    assert 0 <= budget <= len(text), "k out of range"
