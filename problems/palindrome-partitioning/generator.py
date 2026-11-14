"""Seeded inputs for palindrome-partitioning: short strings over tiny alphabets.

The length is n, capped at the constraint of 12. Letters come from a random alphabet of 1 to
3 letters, so palindromic pieces are frequent; a one-letter alphabet gives the worst case of
2^(n-1) partitions (2048 at length 12).
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 12
MAX_ALPHABET = 3


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    alphabet = rng.sample(string.ascii_lowercase, rng.randint(1, MAX_ALPHABET))
    return {"s": "".join(rng.choice(alphabet) for _ in range(length))}


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert set(s) <= set(string.ascii_lowercase), "s must be lowercase letters"
