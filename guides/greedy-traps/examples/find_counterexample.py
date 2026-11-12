"""Check greedy rules against brute force on every small input, smallest first, and print the first
input on which they disagree. Each plausible bug below fails on two or three intervals."""

from collections.abc import Callable, Iterator
from itertools import combinations, product

Interval = tuple[int, int]
Event = tuple[int, int]  # (time, change): +1 opens, -1 closes
LAST_POINT = 3
EVERY_INTERVAL = [(s, e) for s in range(LAST_POINT + 1) for e in range(s + 1, LAST_POINT + 1)]


def small_inputs() -> Iterator[list[Interval]]:
    """Every list of 1 to 3 half-open intervals with endpoints 0 to 3, repeats allowed."""
    for size in (1, 2, 3):
        yield from (list(chosen) for chosen in product(EVERY_INTERVAL, repeat=size))


def half_open_overlap(a: Interval, b: Interval) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def closed_overlap(a: Interval, b: Interval) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def most_by_brute_force(intervals: list[Interval]) -> int:
    return max(
        size
        for size in range(len(intervals) + 1)
        for chosen in combinations(intervals, size)
        if not any(half_open_overlap(a, b) for a, b in combinations(chosen, 2))
    )


def peak_by_brute_force(intervals: list[Interval]) -> int:
    return max(sum(s <= t < e for s, e in intervals) for t in range(LAST_POINT + 1))


def grant(
    intervals: list[Interval],
    key: Callable[[Interval], int],
    overlap: Callable[[Interval, Interval], bool],
) -> int:
    granted: list[Interval] = []
    for interval in sorted(intervals, key=key):
        if not any(overlap(interval, kept) for kept in granted):
            granted.append(interval)
    return len(granted)


def peak(intervals: list[Interval], event_order: Callable[[Event], tuple[int, int]]) -> int:
    events = [(s, +1) for s, _ in intervals] + [(e, -1) for _, e in intervals]
    open_now = highest = 0
    for _, change in sorted(events, key=event_order):
        open_now += change
        highest = max(highest, open_now)
    return highest


def by_start(interval: Interval) -> int:
    return interval[0]


def by_end(interval: Interval) -> int:
    return interval[1]


def closes_first(event: Event) -> tuple[int, int]:
    return event[0], event[1]


def opens_first(event: Event) -> tuple[int, int]:
    return event[0], -event[1]


CHECKS = {
    "most, earliest start": (
        lambda intervals: grant(intervals, by_start, half_open_overlap),
        most_by_brute_force,
    ),
    "most, earliest end, closed test": (
        lambda intervals: grant(intervals, by_end, closed_overlap),
        most_by_brute_force,
    ),
    "most, earliest end": (
        lambda intervals: grant(intervals, by_end, half_open_overlap),
        most_by_brute_force,
    ),
    "peak, opens first at ties": (
        lambda intervals: peak(intervals, opens_first),
        peak_by_brute_force,
    ),
    "peak, closes first at ties": (
        lambda intervals: peak(intervals, closes_first),
        peak_by_brute_force,
    ),
}

inputs = list(small_inputs())
for name, (rule, truth) in CHECKS.items():
    failure = next((i for i in inputs if rule(i) != truth(i)), None)
    if failure is None:
        print(f"{name}: agrees on all {len(inputs)} inputs")
    else:
        print(f"{name}: fails on {failure}, {rule(failure)} instead of {truth(failure)}")
