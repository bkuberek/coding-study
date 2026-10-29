"""Seeded inputs for can-attend-meetings.

Meetings are laid out along the day in time order: each starts after a gap that is 0 (back
to back) two times in three, otherwise 1 to 20 units, and lasts 1 to 60 units; then the list
is shuffled. From 31 meetings on, which covers every ladder size, the schedule never clashes,
so comparing every pair does all n(n-1)/2 comparisons at every seed while sorting costs
n log n. At oracle sizes (30 meetings or fewer) half of the inputs stretch one meeting into
the next one, so the cross-check sees both answers.
"""

import random

MAX_LENGTH = 10**4
MAX_TIME = 10**6
MAX_GAP = 20
MAX_DURATION = 60
CLASH_UP_TO = 30


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    intervals = []
    now = 0
    for _ in range(length):
        now += rng.choice((0, 0, rng.randint(1, MAX_GAP)))
        duration = rng.randint(1, MAX_DURATION)
        intervals.append([now, now + duration])
        now += duration
    if 2 <= length <= CLASH_UP_TO and rng.random() < 0.5:
        position = rng.randrange(length - 1)
        following = intervals[position + 1]
        intervals[position][1] = following[0] + rng.randint(1, following[1] - following[0])
    rng.shuffle(intervals)
    return {"intervals": intervals}


def validate(case_input: dict) -> None:
    intervals = case_input["intervals"]
    assert 0 <= len(intervals) <= MAX_LENGTH, "length out of range"
    for interval in intervals:
        assert len(interval) == 2, "a meeting has a start and an end"
        assert 0 <= interval[0] < interval[1] <= MAX_TIME, "times out of range or not increasing"
