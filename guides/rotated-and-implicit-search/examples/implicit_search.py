"""Binary search without a sorted array in memory: a sequence of unknown length, a sorted sequence split
into chunks of different sizes, a rotated array, and why equal values defeat a rotated array."""

from bisect import bisect_left, bisect_right
from collections.abc import Callable
from itertools import accumulate


def first_true(lo: int, hi: int, is_true: Callable[[int], bool]) -> int:
    """The smallest i in [lo, hi) with is_true(i), or hi when there is none."""
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if is_true(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


# 1. A sorted sequence read one position at a time, whose length is not known in advance.
class Reader:
    """read(i) returns the value at position i, or None past the end, and counts the reads."""

    def __init__(self, values: list[int]) -> None:
        self._values = values
        self.reads = 0

    def read(self, i: int) -> int | None:
        self.reads += 1
        return self._values[i] if i < len(self._values) else None


def first_at_least(reader: Reader, x: int) -> int:
    """The first position whose value is >= x, or the length if there is none. Past the end counts
    as true, as if the sequence went on with values larger than every x."""
    lo, probe = 0, 1
    while (value := reader.read(probe)) is not None and value < x:  # gallop: 1, 2, 4, 8, ...
        print(f"  probe {probe:3}: {value}, below {x}")
        lo, probe = probe + 1, probe * 2
    print(f"  probe {probe:3}: {value}, so the answer is in [{lo}, {probe}]")
    return first_true(lo, probe, lambda i: (v := reader.read(i)) is None or v >= x)


codes = list(range(3, 3 + 7 * 300, 7))  # 300 sorted values: 3, 10, 17, ...
for x in (290, 5000):
    reader = Reader(codes)
    print(f"first value >= {x}:")
    position = first_at_least(reader, x)
    agrees = position == bisect_left(codes, x)
    print(f"  -> position {position} after {reader.reads} reads; bisect_left agrees: {agrees}")

# 2. A sorted sequence split into chunks of different sizes, searched as if it were one array.
chunks = [[2, 3, 5], [7, 11, 13, 17, 19], [23], [29, 31, 37, 41]]
starts = [0, *accumulate(len(chunk) for chunk in chunks)][:-1]  # where each chunk begins: [0, 3, 8, 9]
total = sum(len(chunk) for chunk in chunks)


def element(i: int) -> int:
    chunk = bisect_right(starts, i) - 1  # the last chunk that starts at or before position i
    return chunks[chunk][i - starts[chunk]]


print("chunk starts:", starts, "| the virtual array:", [element(i) for i in range(total)])
i = first_true(0, total, lambda i: element(i) >= 20)
print("first value >= 20 is at virtual position", i, "and is", element(i))

# 3. A rotated sorted array: two increasing runs. "Is position i in the second run?" switches once.
ordered = [3, 9, 14, 20, 26, 31, 40]
moved = 3
rotated = ordered[moved:] + ordered[:moved]  # the first 3 values moved to the back
second_run = [i >= len(ordered) - moved for i in range(len(rotated))]  # known from how it was built
print("rotated:", rotated, "| in the second run:", " ".join("T" if t else "F" for t in second_run))

# 4. With equal values, the first, middle and last elements can look the same for different arrays.
for values in ([2, 2, 2, 0, 2], [2, 0, 2, 2, 2]):
    print(values, "first, middle, last:", values[0], values[len(values) // 2], values[-1], end=" ")
    print("| the smallest is at", values.index(min(values)))
