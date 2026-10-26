"""Seeded inputs for valid-anagram: two strings of length `n`.

`t` is a shuffle of `s`. In about half of the inputs one letter of `t` is then replaced by a
different letter, so the strings are no longer anagrams (answer `false`). The alphabet is
either the first 3 letters or all 26, so small inputs repeat letters often.

Striking letters out of `t` scans from the front each time, so its work grows with n^2 at
every seed: in the `false` case the letter that cannot be matched is usually one of the last
letters of `s`. Equal lengths keep every approach from stopping at the length check.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 5 * 10**4
ALPHABET_SIZES = (3, 26)
MISMATCH_PROBABILITY = 0.5


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    alphabet = string.ascii_lowercase[: rng.choice(ALPHABET_SIZES)]
    s = rng.choices(alphabet, k=length)
    t = s[:]
    rng.shuffle(t)
    if rng.random() < MISMATCH_PROBABILITY:
        position = rng.randrange(length)
        t[position] = rng.choice([letter for letter in alphabet if letter != t[position]])
    return {"s": "".join(s), "t": "".join(t)}


def validate(case_input: dict) -> None:
    for name in ("s", "t"):
        text = case_input[name]
        assert MIN_LENGTH <= len(text) <= MAX_LENGTH, f"{name} length out of range"
        assert all("a" <= letter <= "z" for letter in text), f"{name} has a non-lowercase letter"
