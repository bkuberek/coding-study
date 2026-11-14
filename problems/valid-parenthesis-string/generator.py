"""Seeded inputs for valid-parenthesis-string.

`n` is the length of `s`, clamped to 1..10^4. The generator starts from a random balanced
parenthesis string (or a random string, one time in five), replaces a random share of the
characters by `*` (each wildcard can stand for the character it replaced, so a balanced base
stays valid), and in half of the cases breaks it by flipping one parenthesis. Some strings are
valid only because of their wildcards, some are invalid despite them.

From UNIFORM_FROM characters on (the bench ladder), every input has one shape instead: a
balanced base (one character shorter when n is odd, then closed by a wildcard), half of it
replaced by wildcards, and no break. The string is then always valid, so no approach stops
early, and the set of possible open counts grows by about one per wildcard, which makes
tracking every count quadratic on every seed.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**4
RANDOM_BASE_SHARE = 0.2
BREAK_SHARE = 0.5
UNIFORM_FROM = 100
UNIFORM_STAR_SHARE = 0.5


def _balanced(rng: random.Random, length: int) -> list[str]:
    chars: list[str] = []
    open_count = 0
    for position in range(length):
        remaining = length - position
        if open_count == remaining or (open_count > 0 and rng.random() < 0.5):
            chars.append(")")
            open_count -= 1
        else:
            chars.append("(")
            open_count += 1
    return chars


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= UNIFORM_FROM:
        chars = _balanced(rng, length - length % 2) + ["*"] * (length % 2)
        chars = ["*" if rng.random() < UNIFORM_STAR_SHARE else char for char in chars]
        return {"s": "".join(chars)}
    if length % 2 == 1 or rng.random() < RANDOM_BASE_SHARE:
        chars = [rng.choice("()") for _ in range(length)]
    else:
        chars = _balanced(rng, length)
    star_share = rng.choice((0.05, 0.2, 0.5))
    chars = ["*" if rng.random() < star_share else char for char in chars]
    if rng.random() < BREAK_SHARE:
        position = rng.randrange(length)
        if chars[position] != "*":
            chars[position] = "(" if chars[position] == ")" else ")"
    return {"s": "".join(chars)}


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert set(s) <= set("()*"), "s must contain only (, ) and *"
