"""Seeded inputs for interval-list-intersections.

`n` is the total number of intervals; the split between the two lists is uniform, so either
list may be empty. Each list comes from distinct sorted points over a common range of about
20 * n units, paired up in order, so each list is sorted and strictly separate, and the two
lists interleave densely; about one interval in ten is shrunk to a single point. Intersecting
every pair costs m * n checks (quadratic in n), binary searching partners costs m log n plus
the output, and the two-pointer walk costs m + n.
"""

import random

MAX_LENGTH = 10**5
MAX_VALUE = 10**9


def _separate_intervals(rng: random.Random, count: int, span: int) -> list[list[int]]:
    points = sorted(rng.sample(range(span + 1), 2 * count))
    intervals = []
    for index in range(count):
        start, end = points[2 * index], points[2 * index + 1]
        intervals.append([start, start if rng.random() < 0.1 else end])
    return intervals


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 1), 2 * MAX_LENGTH)
    first = rng.randint(max(0, total - MAX_LENGTH), min(total, MAX_LENGTH))
    span = min(MAX_VALUE, 20 * total)
    return {
        "firstList": _separate_intervals(rng, first, span),
        "secondList": _separate_intervals(rng, total - first, span),
    }


def validate(case_input: dict) -> None:
    for intervals in (case_input["firstList"], case_input["secondList"]):
        assert len(intervals) <= MAX_LENGTH, "length out of range"
        for interval in intervals:
            assert len(interval) == 2, "an interval has two endpoints"
            assert 0 <= interval[0] <= interval[1] <= MAX_VALUE, "endpoints out of range or reversed"
        for left, right in zip(intervals, intervals[1:]):
            assert left[1] < right[0], "intervals must be sorted and separate"
