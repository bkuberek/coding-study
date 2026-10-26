"""Seeded inputs for valid-parentheses: a bracket string of length `n`.

For even lengths, the string starts as a balanced one: a deep nest of n/10 opening brackets,
a random balanced middle (a random walk over the remaining length), and the closers of the
nest. In about half of these strings one character is then replaced by a different bracket,
which always breaks the balance. Odd lengths add one stray bracket to a balanced string of
length n - 1, so they are never balanced.

Below 100 characters, which covers the oracle's inputs, the replaced character is anywhere.
From 100 on, the sizes the ladder times, it is the last character, the outermost closer of the
nest: the answer is still false, but every approach reads the whole string and pair removal
clears everything inside before it gets stuck, as it does on a balanced string. A replacement
anywhere else would stop both approaches at a point that changes from seed to seed.

The nest is the same share of the string at every seed. Pair removal clears at most three of
its levels per pass, so its passes copy at least about n^2/300 characters in all: its work
grows with n^2 at every seed, while the stack reads each character once.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
OPENERS = "([{"
CLOSER_OF = {"(": ")", "[": "]", "{": "}"}
BRACKETS = "()[]{}"
CORRUPT_PROBABILITY = 0.5
NEST_SHARE = 0.2
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    pairs = length // 2
    nest = [rng.choice(OPENERS) for _ in range(round(pairs * NEST_SHARE))]
    middle = _balanced(rng, pairs - len(nest))
    text = nest + middle + [CLOSER_OF[opener] for opener in reversed(nest)]
    if length % 2:
        text.insert(rng.randrange(len(text) + 1), rng.choice(BRACKETS))
    elif text and rng.random() < CORRUPT_PROBABILITY:
        position = len(text) - 1 if length >= UNIFORM_FROM else rng.randrange(len(text))
        text[position] = rng.choice([bracket for bracket in BRACKETS if bracket != text[position]])
    return {"s": "".join(text)}


def _balanced(rng: random.Random, pairs: int) -> list[str]:
    """A random balanced string with `pairs` pairs, built as a random walk."""
    text: list[str] = []
    open_brackets: list[str] = []
    remaining = pairs
    while remaining or open_brackets:
        if remaining and (not open_brackets or rng.random() < 0.5):
            opener = rng.choice(OPENERS)
            open_brackets.append(opener)
            text.append(opener)
            remaining -= 1
        else:
            text.append(CLOSER_OF[open_brackets.pop()])
    return text


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert MIN_LENGTH <= len(s) <= MAX_LENGTH, "length out of range"
    assert all(character in BRACKETS for character in s), "only bracket characters allowed"
