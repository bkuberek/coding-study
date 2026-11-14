"""Seeded inputs for candy-distribution.

`n` is the number of children, clamped to 1..2 * 10^4, with scores in 0..2 * 10^4. Each input
picks one shape: uniform random scores (short runs), long monotone runs of random length
joined at peaks and valleys (where fixing violations one at a time needs many rounds), or a
narrow score range with many equal neighbors.

From UNIFORM_FROM children on (the bench ladder), every input is one peak instead: a rising
run over the first half and a falling run over the second. Each relaxation pass carries the
fix one step back along the falling run, so it needs about n / 2 passes on every seed; with
random run lengths the number of passes would follow the longest falling run a seed drew.
"""

import random

MIN_CHILDREN = 1
MAX_CHILDREN = 2 * 10**4
MAX_SCORE = 2 * 10**4
NARROW_RANGE = 3
UNIFORM_FROM = 100


def _runs(rng: random.Random, count: int) -> list[int]:
    ratings: list[int] = []
    rising = rng.random() < 0.5
    while len(ratings) < count:
        length = rng.randint(1, max(1, count // 3))
        top = rng.randint(length, MAX_SCORE)
        run = list(range(top - length + 1, top + 1))
        ratings.extend(run if rising else run[::-1])
        rising = not rising
    return ratings[:count]


def _peak(rng: random.Random, count: int) -> list[int]:
    rising, falling = count // 2, count - count // 2
    top = rng.randint(max(rising, falling), MAX_SCORE)
    return list(range(top - rising + 1, top + 1)) + list(range(top - 1, top - 1 - falling, -1))


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_CHILDREN), MAX_CHILDREN)
    if count >= UNIFORM_FROM:
        return {"ratings": _peak(rng, count)}
    shape = rng.choice(("uniform", "runs", "narrow"))
    if shape == "runs":
        return {"ratings": _runs(rng, count)}
    high = MAX_SCORE if shape == "uniform" else NARROW_RANGE
    return {"ratings": [rng.randint(0, high) for _ in range(count)]}


def validate(case_input: dict) -> None:
    ratings = case_input["ratings"]
    assert MIN_CHILDREN <= len(ratings) <= MAX_CHILDREN, "number of children out of range"
    assert all(0 <= score <= MAX_SCORE for score in ratings), "score out of range"
