"""Seeded inputs for partition-labels.

`n` is the length of `s`, clamped to 1..10^4. Each input picks one shape:

- blocks: the alphabet is shuffled and split into groups, and the string is a sequence of
  blocks, each written with the letters of its own group, so there are several pieces (up to
  26) and their boundaries are not obvious;
- random: letters drawn from a small random alphabet, which usually gives one long piece.

From UNIFORM_FROM letters on (the bench ladder), every input is blocks with fixed proportions
instead: UNIFORM_BLOCKS blocks of two letters each and equal length. The search for the last
copy of a letter then starts at the end and crosses every later block, about n / 2 letters on
average, on every seed; one long random piece would find each last copy within a few steps.
"""

import random
import string

MIN_LENGTH = 1
MAX_LENGTH = 10**4
UNIFORM_FROM = 100
UNIFORM_BLOCKS = 13


def _blocks(rng: random.Random, length: int) -> str:
    letters = list(string.ascii_lowercase)
    rng.shuffle(letters)
    if length >= UNIFORM_FROM:
        width = len(letters) // UNIFORM_BLOCKS
        groups = [letters[i : i + width] for i in range(0, len(letters), width)]
        share, extra = divmod(length, UNIFORM_BLOCKS)
        sizes = [share + (i < extra) for i in range(UNIFORM_BLOCKS)]
    else:
        groups, sizes = _random_blocks(rng, letters, length)
    return "".join(
        "".join(rng.choice(group) for _ in range(size))
        for group, size in zip(groups, sizes, strict=True)
    )


def _random_blocks(
    rng: random.Random, letters: list[str], length: int
) -> tuple[list[list[str]], list[int]]:
    block_count = rng.randint(1, min(len(letters), length))
    cuts = sorted(rng.sample(range(1, len(letters)), block_count - 1))
    groups = [letters[a:b] for a, b in zip([0, *cuts], [*cuts, len(letters)])]
    sizes = [1] * block_count
    for _ in range(length - block_count):
        sizes[rng.randrange(block_count)] += 1
    return groups, sizes


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= UNIFORM_FROM or rng.random() < 0.8:
        return {"s": _blocks(rng, length)}
    alphabet = rng.sample(string.ascii_lowercase, rng.randint(1, 6))
    return {"s": "".join(rng.choice(alphabet) for _ in range(length))}


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert set(s) <= set(string.ascii_lowercase), "s must contain lowercase letters only"
