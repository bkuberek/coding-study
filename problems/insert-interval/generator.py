"""Seeded inputs for insert-interval.

The existing intervals come from 2n distinct sorted points paired up in order, so they are
sorted and strictly separate; about one in ten is shrunk to a single point. The new interval
is either a random span of the whole value range (three seeds in ten, often swallowing many
intervals) or a short span that covers zero to a few intervals. Every approach copies the
untouched intervals into the output, so the cost is linear (plus a sort for the brute force).
"""

import random

MAX_LENGTH = 10**5
MAX_VALUE = 10**9


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    points = sorted(rng.sample(range(MAX_VALUE + 1), 2 * length))
    intervals = []
    for index in range(length):
        start, end = points[2 * index], points[2 * index + 1]
        intervals.append([start, start if rng.random() < 0.1 else end])
    if rng.random() < 0.3:
        new_start, new_end = sorted(rng.randint(0, MAX_VALUE) for _ in range(2))
    else:
        new_start = rng.randint(0, MAX_VALUE)
        new_end = min(MAX_VALUE, new_start + rng.randint(0, 3 * MAX_VALUE // length))
    return {"intervals": intervals, "newInterval": [new_start, new_end]}


def validate(case_input: dict) -> None:
    intervals, new_interval = case_input["intervals"], case_input["newInterval"]
    assert len(intervals) <= MAX_LENGTH, "length out of range"
    for interval in intervals + [new_interval]:
        assert len(interval) == 2, "an interval has two endpoints"
        assert 0 <= interval[0] <= interval[1] <= MAX_VALUE, "endpoints out of range or reversed"
    for left, right in zip(intervals, intervals[1:]):
        assert left[1] < right[0], "intervals must be sorted and separate"
