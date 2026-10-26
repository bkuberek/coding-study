"""Seeded inputs for interleaving-string: s1 and s2 of total length n, mostly one letter.

The total length is split between s1 and s2 at random (at most 1000 each; one may be empty
for tiny n). Each source is all `a` except for 0 to 4 `b`s at random positions, so both
sources nearly always offer the next character of s3, and a constant share (about a third
or more) of all prefix pairs is reachable, whatever the size. s3 is a random interleaving of
s1 and s2. On three quarters of the seeds one character in the last tenth of s3 is flipped
to the other letter, which usually makes the answer false only after the reachable pairs
have been explored, so even the memoized search does work proportional to m * n; on a few
seeds s3 loses or gains a character instead, to cover the length check, and the rest stay
true. The table approaches always fill (m + 1)(n + 1) cells.
"""

import random

MAX_LENGTH = 1000
MAX_MARKS = 4
FLIP_SHARE = 0.75
LENGTH_CHANGE_SHARE = 0.05


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 0), 2 * MAX_LENGTH)
    low = max(0, total - MAX_LENGTH)
    first_length = rng.randint(max(low, total // 3), min(MAX_LENGTH, total - total // 3))
    s1 = _mostly_a(rng, first_length)
    s2 = _mostly_a(rng, total - first_length)
    sources = [1] * len(s1) + [2] * len(s2)
    rng.shuffle(sources)
    picked = {1: iter(s1), 2: iter(s2)}
    s3 = [next(picked[source]) for source in sources]
    roll = rng.random()
    if roll < FLIP_SHARE and s3:
        position = rng.randint(len(s3) - 1 - len(s3) // 10, len(s3) - 1)
        s3[position] = "b" if s3[position] == "a" else "a"
    elif roll < FLIP_SHARE + LENGTH_CHANGE_SHARE / 2 and s3:
        del s3[rng.randrange(len(s3))]
    elif roll < FLIP_SHARE + LENGTH_CHANGE_SHARE:
        s3.insert(rng.randint(0, len(s3)), rng.choice("ab"))
    return {"s1": s1, "s2": s2, "s3": "".join(s3)}


def _mostly_a(rng: random.Random, length: int) -> str:
    characters = ["a"] * length
    for position in rng.sample(range(length), min(length, rng.randint(0, MAX_MARKS))):
        characters[position] = "b"
    return "".join(characters)


def validate(case_input: dict) -> None:
    s1, s2, s3 = case_input["s1"], case_input["s2"], case_input["s3"]
    assert len(s1) <= MAX_LENGTH and len(s2) <= MAX_LENGTH, "source too long"
    assert len(s3) <= 2 * MAX_LENGTH, "s3 too long"
    for text in (s1, s2, s3):
        assert all("a" <= character <= "z" for character in text), "only lowercase letters"
