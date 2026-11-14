"""Seeded inputs for longest-palindromic-substring.

`n` is the length of `s`, clamped to 1..1000. Each input draws an alphabet of 1, 2, 3, 10 or
62 characters (letters and digits): tiny alphabets create many overlapping palindromes and long
expansions, large ones make long palindromes rare. Half of the inputs also overwrite a random
window with a planted palindrome, so the answer is often long and not at either end.

From RUN_FROM characters on (the bench ladder), every input is the worst case instead: a run
of one random character. Every center then expands to the nearer end, so expanding around
centers costs about n^2 / 2 steps on every seed, where a varied text would let most
expansions stop after a step or two.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 1000
CHARACTERS = string.ascii_letters + string.digits
ALPHABET_SIZES = (1, 2, 3, 10, 62)
PLANT_SHARE = 0.5
RUN_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= RUN_FROM:
        return {"s": rng.choice(CHARACTERS) * length}
    alphabet = rng.sample(CHARACTERS, rng.choice(ALPHABET_SIZES))
    chars = [rng.choice(alphabet) for _ in range(length)]
    if rng.random() < PLANT_SHARE:
        size = rng.randint(1, length)
        half = [rng.choice(alphabet) for _ in range(size // 2)]
        middle = [rng.choice(alphabet)] if size % 2 == 1 else []
        start = rng.randint(0, length - size)
        chars[start : start + size] = half + middle + half[::-1]
    return {"s": "".join(chars)}


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert set(s) <= set(CHARACTERS), "s must contain only letters and digits"
