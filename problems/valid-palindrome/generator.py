"""Seeded inputs for valid-palindrome: near-palindromes padded with ignored characters.

The letters and digits of every input form a palindrome, except that half of the inputs
change one character just left of the middle. Both outcomes therefore need a scan of
about half of the string, so the work is linear in n at every seed. A fifth of the
characters are spaces and punctuation at every seed, so the share of characters to skip
does not change along the ladder. Letters get a random case, so a solution must both skip
ignored characters and compare letters case-insensitively.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 2 * 10**5
ALPHANUMERIC = string.ascii_lowercase + string.digits
IGNORED = " " + string.punctuation
IGNORED_SHARE = 0.2


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    kept_count = max(1, length - round(length * IGNORED_SHARE))
    kept = _palindrome(rng, kept_count)
    if kept_count >= 2 and rng.random() < 0.5:
        _break_near_middle(rng, kept)
    kept = [ch.upper() if ch.isalpha() and rng.random() < 0.5 else ch for ch in kept]
    ignored_positions = set(rng.sample(range(length), length - kept_count))
    characters = iter(kept)
    text = "".join(
        rng.choice(IGNORED) if index in ignored_positions else next(characters)
        for index in range(length)
    )
    return {"s": text}


def validate(case_input: dict) -> None:
    text = case_input["s"]
    assert MIN_LENGTH <= len(text) <= MAX_LENGTH, "length out of range"
    assert all(32 <= ord(ch) <= 126 for ch in text), "only printable ASCII is allowed"


def _palindrome(rng: random.Random, count: int) -> list[str]:
    half = [rng.choice(ALPHANUMERIC) for _ in range(count // 2)]
    middle = [rng.choice(ALPHANUMERIC)] if count % 2 else []
    return half + middle + half[::-1]


def _break_near_middle(rng: random.Random, kept: list[str]) -> None:
    half = len(kept) // 2
    index = rng.randint(max(0, half - max(1, half // 10)), half - 1)
    kept[index] = rng.choice([ch for ch in ALPHANUMERIC if ch != kept[index]])
