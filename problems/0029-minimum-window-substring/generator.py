"""Seeded inputs for minimum-window-substring: a rare letter forces long windows.

Each input picks an alphabet of 4, 10 or 52 English letters. One of them, the rare letter,
appears about 40 times in s; the others fill the rest uniformly. The required string t
holds the rare letter 1 to 4 times plus up to 5 common letters. Covering t then needs a
window that spans 1 to 4 rare occurrences, about n/40 to n/10 characters, so growing a
window from every start costs on the order of n^2 / 16 steps at every seed.

Large inputs always contain enough letters, so the answer is a real window. Small inputs
can lack a required letter, which gives the oracle cross-check empty answers too.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**5
ALPHABET_SIZES = (4, 10, 52)
RARE_OCCURRENCES = 40


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    alphabet = rng.sample(string.ascii_letters, rng.choice(ALPHABET_SIZES))
    rare, common = alphabet[0], alphabet[1:]
    rare_share = min(0.5, RARE_OCCURRENCES / length)
    text = "".join(rare if rng.random() < rare_share else rng.choice(common) for _ in range(length))
    required = [rare] * rng.randint(1, 4) + rng.choices(common, k=rng.randint(0, 5))
    rng.shuffle(required)
    return {"s": text, "t": "".join(required)}


def validate(case_input: dict) -> None:
    for name in ("s", "t"):
        value = case_input[name]
        assert MIN_LENGTH <= len(value) <= MAX_LENGTH, f"{name} length out of range"
        assert all(ch in string.ascii_letters for ch in value), f"{name} must be English letters"
