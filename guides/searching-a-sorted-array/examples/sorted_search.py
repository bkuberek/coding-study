"""Binary search on a sorted array, on a half-open and on a closed interval, with a trace and a count."""

from collections.abc import Callable
from math import floor, log2

Step = Callable[[int, int, int], None]


def search_half_open(items: list[int], target: int, on_step: Step | None = None) -> int:
    """The index of target in items, or -1. If target is present, it is in items[lo:hi]."""
    lo, hi = 0, len(items)
    while lo < hi:  # [lo, hi) still holds at least one candidate
        mid = lo + (hi - lo) // 2
        if on_step:
            on_step(lo, hi, mid)
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1  # mid and everything before it are too small
        else:
            hi = mid  # mid and everything after it are too big; hi itself is never a candidate
    return -1


def search_closed(items: list[int], target: int) -> int:
    """The same search on [lo, hi], where both ends are candidates."""
    lo, hi = 0, len(items) - 1
    while lo <= hi:  # [lo, hi] still holds at least one candidate
        mid = lo + (hi - lo) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1  # hi is a candidate, so it must step past mid
    return -1


def show(lo: int, hi: int, mid: int) -> None:
    interval = f"[{lo}, {hi})"
    print(f"  {interval:8}  size {hi - lo:2}  mid {mid:2}  value {values[mid]}")


values = [4, 9, 15, 23, 31, 38, 42, 50, 57, 61, 70, 77, 83, 91, 96]
for target in (61, 40):
    print(f"search {target}:")
    print("  ->", search_half_open(values, target, show))

# Both versions agree with a linear scan on every prefix of the array, for every target.
agree = all(
    search_half_open(values[:n], t) == search_closed(values[:n], t)
    == (values[:n].index(t) if t in values[:n] else -1)
    for n in range(len(values) + 1)
    for t in range(100)
)
print("half-open, closed and a linear scan agree:", agree)

# The interval at least halves on every step, so the loop runs at most floor(log2 n) + 1 times.
for n in (1, 2, 3, 15, 16, 100, 1024):
    evens = list(range(0, 2 * n, 2))
    worst = 0
    for t in range(-1, 2 * n + 1):
        steps: list[int] = []
        search_half_open(evens, t, lambda lo, hi, mid: steps.append(mid))
        worst = max(worst, len(steps))
    print(f"n = {n:4}: at most {worst:2} steps, floor(log2 n) + 1 = {floor(log2(n)) + 1}")
