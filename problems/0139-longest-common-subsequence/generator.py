"""Seeded inputs for longest-common-subsequence: string pairs of total length n.

The total length is split between the two strings at random (each gets at least a third,
and at most 1000 characters). The alphabet has 2, 4, 8 or 26 letters. Half of the seeds draw
the strings independently; the other half derive the second string from the first by random
deletions, insertions and substitutions, so the answer is long. Every table approach fills
all m * n cells, about n^2 / 4 for a balanced split.
"""

import random
import string

MAX_LENGTH = 1000
ALPHABET_SIZES = (2, 4, 8, 26)
EDIT_PROBABILITY = 0.2


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 2), 2 * MAX_LENGTH)
    third = max(1, total // 3)
    first_length = min(MAX_LENGTH, rng.randint(third, total - third))
    second_length = min(MAX_LENGTH, max(1, total - first_length))
    letters = string.ascii_lowercase[: rng.choice(ALPHABET_SIZES)]
    text1 = "".join(rng.choices(letters, k=first_length))
    if rng.random() < 0.5:
        text2 = "".join(rng.choices(letters, k=second_length))
    else:
        text2 = _mutate(rng, text1, letters, second_length)
    return {"text1": text1, "text2": text2}


def _mutate(rng: random.Random, text: str, letters: str, length: int) -> str:
    result: list[str] = []
    for character in text:
        roll = rng.random()
        if roll < EDIT_PROBABILITY / 2:
            continue
        if roll < EDIT_PROBABILITY:
            result.append(rng.choice(letters))
        result.append(character)
    while len(result) < length:
        result.insert(rng.randint(0, len(result)), rng.choice(letters))
    return "".join(result[:length])


def validate(case_input: dict) -> None:
    for name in ("text1", "text2"):
        text = case_input[name]
        assert 1 <= len(text) <= MAX_LENGTH, f"{name} length out of range"
        assert all("a" <= character <= "z" for character in text), f"{name} must be lowercase"
