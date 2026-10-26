"""Seeded inputs for min-meeting-rooms.

Starts are uniform over a day of 50 * n time units and durations between 5 and 2000 units,
both on a grid of 5, so about 20 meetings run at once and many meetings start exactly when
another ends. Counting the meetings running at every start compares every pair (quadratic
at every seed); the heap and the sorted sweep sort once.
"""

import random

MAX_LENGTH = 10**5
MAX_VALUE = 10**9
GRID = 5
MAX_DURATION = 400


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    day = 10 * length
    intervals = []
    for _ in range(length):
        start = GRID * rng.randint(0, day)
        intervals.append([start, start + GRID * rng.randint(1, MAX_DURATION)])
    return {"intervals": intervals}


def validate(case_input: dict) -> None:
    intervals = case_input["intervals"]
    assert 1 <= len(intervals) <= MAX_LENGTH, "length out of range"
    for interval in intervals:
        assert len(interval) == 2, "a meeting has a start and an end"
        assert 0 <= interval[0] < interval[1] <= MAX_VALUE, "times out of range or not increasing"
