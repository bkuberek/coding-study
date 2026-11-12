"""Seeded inputs for substring-search: a text and a pattern over letters and digits.

From 100 letters on, the sizes the ladder times, the text is `n` copies of "a" and the pattern
is "a" repeated n/2 - 1 times and then "b". Comparing the pattern at every start then matches
n/2 - 1 letters before it fails at each of the n/2 + 1 starts (about n^2 / 4 comparisons) at
every seed, and no window of the text hashes like the pattern, so a rolling hash never has to
verify a window. Half of the seeds change the last letter of the text to "b", so that the
pattern occurs once, at the very end.

Below 100 letters, which covers the oracle's inputs, the alphabet has one to five symbols, so
that occurrences are frequent and overlap; the pattern is a piece of the text in half of the
inputs and random in the others, and now and then it is longer than the text.
"""

import random

MAX_LENGTH = 10**5
LADDER_FROM = 100
ALPHABETS = ("a", "ab", "abc", "aAb1", "abcAB")
MAX_SMALL_PATTERN = 8


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length >= LADDER_FROM:
        pattern = "a" * (length // 2 - 1) + "b"
        last = "b" if rng.random() < 0.5 else "a"
        return {"text": "a" * (length - 1) + last, "pattern": pattern}
    alphabet = rng.choice(ALPHABETS)
    text = "".join(rng.choice(alphabet) for _ in range(length))
    if rng.random() < 0.5:
        size = rng.randint(1, min(length, MAX_SMALL_PATTERN))
        start = rng.randint(0, length - size)
        pattern = text[start : start + size]
    else:
        size = rng.randint(1, min(length + 1, MAX_SMALL_PATTERN))
        pattern = "".join(rng.choice(alphabet) for _ in range(size))
    return {"text": text, "pattern": pattern}


def validate(case_input: dict) -> None:
    text, pattern = case_input["text"], case_input["pattern"]
    assert 1 <= len(text) <= MAX_LENGTH, "text length out of range"
    assert 1 <= len(pattern) <= MAX_LENGTH, "pattern length out of range"
    assert text.isascii() and text.isalnum(), "text must hold ASCII letters and digits only"
    assert pattern.isascii() and pattern.isalnum(), "pattern must hold ASCII letters and digits only"
