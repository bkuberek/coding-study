"""Seeded inputs for job-scheduling-max-profit.

`n` is the number of jobs, clamped to 1..2000, with profits in 1..10^4. Each input picks a time
horizon: dense (about 3n time units, so most jobs overlap several others), sparse (about 50n
units, long gaps), or wide (the whole range up to 10^9). Durations are drawn up to a fraction
of the horizon, with a share of very short jobs. Jobs are listed in random order. In the dense
shape the backward scan of the quadratic method passes many overlapping jobs, so it shows its
quadratic growth.

From UNIFORM_FROM jobs on (the bench ladder), every input uses the dense horizon with
durations up to half of it, so each job overlaps a fixed share of the others on every seed
and the backward scan grows as n^2; a seed that drew the sparse or wide horizon would make it
nearly linear.
"""

import random

MIN_JOBS = 1
MAX_JOBS = 2000
MAX_TIME = 10**9
MAX_PROFIT = 10**4
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_JOBS), MAX_JOBS)
    uniform = count >= UNIFORM_FROM
    shape = "dense" if uniform else rng.choice(("dense", "sparse", "wide"))
    horizon = {"dense": 3 * count + 10, "sparse": 50 * count + 10, "wide": MAX_TIME}[shape]
    longest = max(2, horizon // (2 if uniform else rng.choice((4, 20, 100))))
    jobs = []
    for _ in range(count):
        duration = rng.randint(1, 3) if rng.random() < 0.2 else rng.randint(1, longest)
        start = rng.randint(1, horizon - 1)
        end = min(horizon, start + duration)
        jobs.append((start, end, rng.randint(1, MAX_PROFIT)))
    rng.shuffle(jobs)
    return {
        "startTime": [start for start, _, _ in jobs],
        "endTime": [end for _, end, _ in jobs],
        "profit": [pay for _, _, pay in jobs],
    }


def validate(case_input: dict) -> None:
    starts, ends, profits = case_input["startTime"], case_input["endTime"], case_input["profit"]
    assert MIN_JOBS <= len(starts) <= MAX_JOBS, "number of jobs out of range"
    assert len(starts) == len(ends) == len(profits), "arrays differ in length"
    assert all(1 <= s < e <= MAX_TIME for s, e in zip(starts, ends)), "invalid job interval"
    assert all(1 <= pay <= MAX_PROFIT for pay in profits), "profit out of range"
