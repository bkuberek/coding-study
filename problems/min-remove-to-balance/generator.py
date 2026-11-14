"""Seeded inputs for min-remove-to-balance: a string of length `n` that needs Theta(n) deletions.

The base is a balanced string of letters and parentheses, built as a random walk that never
closes more than it opened and closes everything by the end. Between n/20 and n/10 stray
parentheses (at least one is possible even for tiny `n`) are then inserted at positions where
the base is at depth 0, all stray `)` before all stray `(`. A stray `)` at depth 0 can never be
matched and a stray `(` after the last stray `)` is never closed, so exactly the strays have
to go: the minimum number of deletions is their count.

Deleting one offending parenthesis per rescan therefore needs n/20 to n/10 scans of the
string, which grows with n^2 at every seed; the stack and the two passes stay linear.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**5
LETTER_PROBABILITY = 0.4
OPEN_PROBABILITY = 0.3


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    strays = rng.randint(length // 20, max(1, length // 10))
    base, top_level = _balanced(rng, length - strays)
    closers = rng.randint(0, strays)
    points = sorted(rng.choice(top_level) for _ in range(strays))
    characters = list(base)
    # Insert from the back so earlier insertion points stay valid; ties keep closers first.
    for k in reversed(range(strays)):
        characters.insert(points[k], ")" if k < closers else "(")
    return {"s": "".join(characters)}


def _balanced(rng: random.Random, size: int) -> tuple[str, list[int]]:
    """A balanced string of `size` characters and the positions where its depth is 0."""
    characters: list[str] = []
    top_level = [0]
    depth = 0
    for position in range(size):
        remaining = size - position
        roll = rng.random()
        if depth == remaining:
            character = ")"
        elif roll < LETTER_PROBABILITY:
            character = rng.choice(string.ascii_lowercase)
        elif roll < LETTER_PROBABILITY + OPEN_PROBABILITY and depth + 1 < remaining:
            character = "("
        elif depth:
            character = ")"
        else:
            character = rng.choice(string.ascii_lowercase)
        depth += {"(": 1, ")": -1}.get(character, 0)
        characters.append(character)
        if depth == 0:
            top_level.append(position + 1)
    return "".join(characters), top_level


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert all(character in "()" or "a" <= character <= "z" for character in s), "bad character"
