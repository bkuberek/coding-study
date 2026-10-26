"""Seeded inputs for min-interval-per-query.

There are n intervals and n queries over a line of 20 * n points. Interval lengths mix short
ones (up to 10 points) and long ones (up to 1000 points), so a typical point is covered by a
few intervals of very different sizes and a few points are covered by none. Queries are
uniform over the line, extended slightly past both ends, and may repeat. Scanning every
interval for every query costs n * q (quadratic in n); both sorted approaches cost about
(n + q) log(n + q).
"""

import random

MAX_LENGTH = 10**5
MAX_VALUE = 10**7
SHORT = 10
LONG = 1000


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    line = 20 * length
    intervals = []
    for _ in range(length):
        left = rng.randint(1, line)
        span = rng.randint(1, SHORT if rng.random() < 0.5 else LONG)
        intervals.append([left, min(MAX_VALUE, left + span - 1)])
    queries = [rng.randint(1, min(MAX_VALUE, line + LONG)) for _ in range(length)]
    return {"intervals": intervals, "queries": queries}


def validate(case_input: dict) -> None:
    intervals, queries = case_input["intervals"], case_input["queries"]
    assert 1 <= len(intervals) <= MAX_LENGTH, "too many or too few intervals"
    assert 1 <= len(queries) <= MAX_LENGTH, "too many or too few queries"
    for interval in intervals:
        assert len(interval) == 2, "an interval has two endpoints"
        assert 1 <= interval[0] <= interval[1] <= MAX_VALUE, "endpoints out of range or reversed"
    assert all(1 <= query <= MAX_VALUE for query in queries), "query out of range"
