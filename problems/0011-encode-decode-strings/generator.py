"""Seeded inputs for encode-decode-strings: `n` strings of 0 to 12 characters.

About half of the characters come from the ones that break naive formats (`#`, `,`, `\\`,
`:`, `|`, digits and space); the rest are any printable ASCII character, a tab or a newline.
About a tenth of the strings are empty. Both approaches do O(1) work per character, so their
time grows linearly with `n`.
"""

import random

MIN_STRINGS = 0
MAX_STRINGS = 10**5
MAX_STRING_LENGTH = 200
MAX_TOTAL_LENGTH = 10**6
GENERATED_MAX_LENGTH = 12
EMPTY_PROBABILITY = 0.1
SPECIAL_PROBABILITY = 0.5
SPECIAL = "#,\\:|0123456789 "
PRINTABLE = "".join(chr(code) for code in range(32, 127)) + "\t\n"


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_STRINGS), MAX_STRINGS)
    return {"strs": [_string(rng) for _ in range(count)]}


def _string(rng: random.Random) -> str:
    if rng.random() < EMPTY_PROBABILITY:
        return ""
    length = rng.randint(1, GENERATED_MAX_LENGTH)
    return "".join(
        rng.choice(SPECIAL) if rng.random() < SPECIAL_PROBABILITY else rng.choice(PRINTABLE)
        for _ in range(length)
    )


def validate(case_input: dict) -> None:
    strs = case_input["strs"]
    assert MIN_STRINGS <= len(strs) <= MAX_STRINGS, "string count out of range"
    assert sum(len(text) for text in strs) <= MAX_TOTAL_LENGTH, "too many characters"
    for text in strs:
        assert len(text) <= MAX_STRING_LENGTH, "string too long"
        assert all(character in PRINTABLE for character in text), "character out of range"
