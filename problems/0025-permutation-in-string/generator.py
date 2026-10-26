"""Seeded inputs for permutation-in-string: one planted window decides the answer.

The pattern has between n/8 and n/4 letters, where n is the text length, drawn from an
alphabet of 3, 6 or 26 letters. One letter of that alphabet, the marker, appears in the
pattern at least once but never in the background of the text. A shuffled copy of the
pattern is planted in the back half of the text. In half of the inputs one marker in the
copy is replaced by another letter, so the text holds fewer markers than the pattern
needs and the answer is false; otherwise the planted copy is the only window with enough
markers and the answer is true.

Because the planted window sits late, sorting every window before it costs about
n * m log m steps at every seed, while the sliding windows stay linear.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**5
ALPHABET_SIZES = (3, 6, 26)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    alphabet = rng.sample(string.ascii_lowercase, rng.choice(ALPHABET_SIZES))
    marker, background = alphabet[0], alphabet[1:]
    width = rng.randint(max(1, length // 8), max(1, length // 4))
    pattern = [marker] + rng.choices(alphabet, k=width - 1)
    rng.shuffle(pattern)
    planted = pattern[:]
    rng.shuffle(planted)
    if rng.random() < 0.5:
        planted[planted.index(marker)] = rng.choice(background)
    text = rng.choices(background, k=length)
    start = rng.randint(min(length // 2, length - width), length - width)
    text[start : start + width] = planted
    return {"pattern": "".join(pattern), "text": "".join(text)}


def validate(case_input: dict) -> None:
    for name in ("pattern", "text"):
        value = case_input[name]
        assert MIN_LENGTH <= len(value) <= MAX_LENGTH, f"{name} length out of range"
        assert all("a" <= ch <= "z" for ch in value), f"{name} must be lowercase letters"
