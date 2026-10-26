"""Seeded inputs for merge-intervals: about n/4 separated groups of overlapping intervals.

Group g owns the region [g * spacing, g * spacing + width] around a center point; every
interval of the group starts at or before the center and ends at or after it, so the group
merges into one interval (touching at the center counts). Gaps between regions keep groups
apart. Intervals are dealt to groups at random, every group gets at least one, and the list
is shuffled. The merged set therefore holds about n/4 intervals during most of the input,
so absorbing intervals one by one costs about n^2/8 comparisons, while sorting costs
n log n.
"""

import random

MAX_LENGTH = 10**4
MAX_VALUE = 10**9
SPACING = 10**5
WIDTH = SPACING // 2


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    groups = max(1, length // 4)
    owners = list(range(groups)) + [rng.randrange(groups) for _ in range(length - groups)]
    intervals = []
    for group in owners:
        low = group * SPACING
        center = low + rng.randint(0, WIDTH)
        start = rng.randint(low, center)
        end = rng.randint(center, low + WIDTH)
        intervals.append([start, end])
    rng.shuffle(intervals)
    return {"intervals": intervals}


def validate(case_input: dict) -> None:
    intervals = case_input["intervals"]
    assert 1 <= len(intervals) <= MAX_LENGTH, "length out of range"
    for interval in intervals:
        assert len(interval) == 2, "an interval has two endpoints"
        assert 0 <= interval[0] <= interval[1] <= MAX_VALUE, "endpoints out of range or reversed"
