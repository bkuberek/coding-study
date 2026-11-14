"""Seeded inputs for remove-covered-intervals.

n distinct intervals with starts uniform over [0, 10n) and lengths from 1 to 50, so about
2.5 intervals contain a typical point at every size and roughly half of the intervals are
covered. An interval that is not covered is compared with all the others by the pairwise
check, which keeps it quadratic at every seed; sorting costs n log n. Below 31 intervals,
half of the inputs use starts in [0, 20) and lengths up to 12 instead, which nests intervals
and repeats starts and ends far more often.
"""

import random

MAX_LENGTH = 10**4
MAX_VALUE = 10**5
SPREAD = 10
MAX_SPAN = 50
DENSE_UP_TO = 30


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length <= DENSE_UP_TO and rng.random() < 0.5:
        starts, longest = 20, 12
    else:
        starts, longest = SPREAD * length, MAX_SPAN
    seen: set[tuple[int, int]] = set()
    intervals = []
    while len(intervals) < length:
        start = rng.randrange(starts)
        end = min(MAX_VALUE, start + rng.randint(1, longest))
        if start < end and (start, end) not in seen:
            seen.add((start, end))
            intervals.append([start, end])
    return {"intervals": intervals}


def validate(case_input: dict) -> None:
    intervals = case_input["intervals"]
    assert 1 <= len(intervals) <= MAX_LENGTH, "length out of range"
    assert len({tuple(interval) for interval in intervals}) == len(intervals), (
        "intervals must be distinct"
    )
    for interval in intervals:
        assert len(interval) == 2, "an interval has two endpoints"
        assert 0 <= interval[0] < interval[1] <= MAX_VALUE, (
            "endpoints out of range or not increasing"
        )
