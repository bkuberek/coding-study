"""Seeded inputs for edit-distance: word pairs of total length n.

The total length is split between the two words at random (at most 500 letters each; for
tiny n one word may be empty). The alphabet has 2, 4 or 26 letters. Half of the seeds draw
the words independently; the other half derive the second word from the first with random
insertions, deletions and replacements, so the distance is small relative to the lengths.
Every table approach fills all (m + 1)(n + 1) cells.
"""

import random
import string

MAX_LENGTH = 500
ALPHABET_SIZES = (2, 4, 26)
EDIT_PROBABILITY = 0.15


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 1), 2 * MAX_LENGTH)
    low = max(0, total - MAX_LENGTH)
    first_length = rng.randint(max(low, total // 3), min(MAX_LENGTH, total - total // 3))
    second_length = total - first_length
    letters = string.ascii_lowercase[: rng.choice(ALPHABET_SIZES)]
    word1 = "".join(rng.choices(letters, k=first_length))
    if rng.random() < 0.5:
        word2 = "".join(rng.choices(letters, k=second_length))
    else:
        word2 = _edit(rng, word1, letters, second_length)
    return {"word1": word1, "word2": word2}


def _edit(rng: random.Random, word: str, letters: str, length: int) -> str:
    result: list[str] = []
    for character in word:
        roll = rng.random()
        if roll < EDIT_PROBABILITY / 3:
            continue
        if roll < 2 * EDIT_PROBABILITY / 3:
            result.append(rng.choice(letters))
        elif roll < EDIT_PROBABILITY:
            character = rng.choice(letters)
        result.append(character)
    while len(result) < length:
        result.insert(rng.randint(0, len(result)), rng.choice(letters))
    return "".join(result[:length])


def validate(case_input: dict) -> None:
    for name in ("word1", "word2"):
        word = case_input[name]
        assert 0 <= len(word) <= MAX_LENGTH, f"{name} length out of range"
        assert all("a" <= character <= "z" for character in word), f"{name} must be lowercase"
