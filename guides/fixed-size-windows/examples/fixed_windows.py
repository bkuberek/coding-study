"""Slide a window of k values: one value enters, one leaves, and the summary is updated."""

import math
from collections import deque
from itertools import islice


def rolling_sums(values: list[int], k: int) -> list[int]:
    """The sum of every window of k consecutive values."""
    total = sum(values[:k])  # the first window, built once
    sums = [total]
    for right in range(k, len(values)):
        total += values[right] - values[right - k]  # one value enters, one leaves
        sums.append(total)
    return sums


rain = [3, 0, 4, 1, 0, 0, 6, 2]
print("3-day rainfall totals:", rolling_sums(rain, 3))
print("recomputed each time: ", [sum(rain[i:i + 3]) for i in range(len(rain) - 2)])


def distinct_per_window(values: list[int], k: int) -> list[int]:
    """How many different values each window of k holds, with a count per value."""
    counts: dict[int, int] = {}
    result = []
    for right, entering in enumerate(values):
        counts[entering] = counts.get(entering, 0) + 1
        left = right - k + 1  # where the window that ends at `right` starts
        if left < 0:
            continue  # the first window is not full yet
        print(f"  window {left}..{right} {values[left:right + 1]}: {len(counts)} distinct")
        result.append(len(counts))
        leaving = values[left]
        counts[leaving] -= 1
        if counts[leaving] == 0:
            del counts[leaving]  # a zero count left behind would still be counted by len()
    return result


visits = [4, 4, 1, 3, 4, 2, 2, 2, 5]
print("distinct values in each window of 4 of", visits)
sliding = distinct_per_window(visits, 4)
print("sliding:", sliding, "| recomputed:", [len(set(visits[i:i + 4])) for i in range(6)])


def sliding_window(iterable, n):  # the recipe of the itertools documentation
    iterator = iter(iterable)
    window = deque(islice(iterator, n - 1), maxlen=n)
    for x in iterator:
        window.append(x)  # a full deque drops its oldest value by itself
        yield tuple(window)


print("windows of 3 from the recipe:", [sum(window) for window in sliding_window(rain, 3)])

floats = [1e16, 1.0, 1.0]
rolling = floats[0] + floats[1]  # the first window of 2; the 1.0 is rounded away
rolling -= floats[0]  # slide: 1e16 leaves...
rolling += floats[2]  # ...and 1.0 enters
print("rolling float sum of [1.0, 1.0]:", rolling, "| math.fsum:", math.fsum(floats[1:]))
