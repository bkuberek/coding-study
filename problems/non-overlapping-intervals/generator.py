"""Seeded inputs for non-overlapping-intervals.

Starts are spread over a window of about 100 * n units and lengths are between 10 and 200
units, both on a grid of 10, so a typical interval overlaps one or two others and many
intervals touch exactly at an endpoint. The chain dynamic program compares every pair
(quadratic at every seed); the greedy approaches sort once.
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
GRID = 10
MAX_SPAN = 20


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    window = 5 * length
    intervals = []
    for _ in range(length):
        start = GRID * rng.randint(-window, window)
        intervals.append([start, start + GRID * rng.randint(1, MAX_SPAN)])
    return {"intervals": intervals}


def validate(case_input: dict) -> None:
    intervals = case_input["intervals"]
    assert 1 <= len(intervals) <= MAX_LENGTH, "length out of range"
    for interval in intervals:
        assert len(interval) == 2, "an interval has two endpoints"
        assert -VALUE_LIMIT <= interval[0] < interval[1] <= VALUE_LIMIT, "endpoints out of range or not increasing"
