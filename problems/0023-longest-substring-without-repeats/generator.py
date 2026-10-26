"""Seeded inputs for longest-substring-without-repeats: shuffled runs over a chosen alphabet.

Each input picks an alphabet of 2, 10, 26 or all 95 printable characters and concatenates
random permutations of it, so substrings without repeats are as long as the alphabet
allows. A few random characters are sprinkled in to break runs at unpredictable places.
Growing a window from every start then costs about n times the alphabet size, while the
sliding windows touch each character at most twice.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 5 * 10**4
PRINTABLE = "".join(chr(code) for code in range(32, 127))
ALPHABETS = ("ab", string.digits, string.ascii_lowercase, PRINTABLE)
NOISE_SHARE = 0.05


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    alphabet = list(rng.choice(ALPHABETS))
    characters: list[str] = []
    while len(characters) < length:
        rng.shuffle(alphabet)
        for ch in alphabet:
            characters.append(rng.choice(alphabet) if rng.random() < NOISE_SHARE else ch)
    return {"s": "".join(characters[:length])}


def validate(case_input: dict) -> None:
    text = case_input["s"]
    assert len(text) <= MAX_LENGTH, "length out of range"
    assert all(32 <= ord(ch) <= 126 for ch in text), "only printable ASCII is allowed"
