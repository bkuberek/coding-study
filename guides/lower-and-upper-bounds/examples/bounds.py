"""Lower and upper bounds: the first position where a yes/no question about a sorted array turns true."""

from bisect import bisect_left, bisect_right
from collections.abc import Callable


def first_true(lo: int, hi: int, is_true: Callable[[int], bool]) -> int:
    """The smallest i in [lo, hi) with is_true(i), or hi when there is none.

    Assumes is_true is false, ..., false, then true, ..., true on [lo, hi).
    Invariant: is_true is false everywhere before lo, and true from hi on.
    """
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if is_true(mid):
            hi = mid  # mid may be the first true position: keep it as the end
        else:
            lo = mid + 1  # mid is false, so the first true position is after it
    return lo


def lower_bound(items: list[int], x: int) -> int:
    """The first position whose value is >= x."""
    return first_true(0, len(items), lambda i: items[i] >= x)


def upper_bound(items: list[int], x: int) -> int:
    """The first position whose value is > x."""
    return first_true(0, len(items), lambda i: items[i] > x)


weights = [3, 5, 5, 8, 8, 8, 12, 15, 19, 19, 24, 30]
print("weights:  ", weights)
print("w >= 8:   ", " ".join("T" if w >= 8 else "F" for w in weights))
print("w >  8:   ", " ".join("T" if w > 8 else "F" for w in weights))
print("lower_bound(8) =", lower_bound(weights, 8), "| upper_bound(8) =", upper_bound(weights, 8))
print("how many weigh 8:", upper_bound(weights, 8) - lower_bound(weights, 8))
print("10 is absent, both bounds agree:", lower_bound(weights, 10), upper_bound(weights, 10))

# Range counts: the parcels weighing from 5 to 19, both included.
start, stop = lower_bound(weights, 5), upper_bound(weights, 19)
print(f"weights in 5..19: {stop - start}, {weights[start:stop]}")

# The neighbours of an absent value: the lightest of at least 10, the heaviest below 10.
i = lower_bound(weights, 10)
print("lightest >= 10:", weights[i] if i < len(weights) else None, "| heaviest < 10:", weights[i - 1] if i > 0 else None)

# The edges: a bound can be 0 or len(weights), so check before reading weights[i].
print("lower_bound(1) =", lower_bound(weights, 1), "| lower_bound(99) =", lower_bound(weights, 99))

# bisect computes the same bounds, for every value, present or not.
agrees = all(
    lower_bound(weights, x) == bisect_left(weights, x) and upper_bound(weights, x) == bisect_right(weights, x)
    for x in range(35)
)
print("bisect_left and bisect_right agree for 0..34:", agrees)

# key= (Python 3.10+) searches records by a field. The key is not applied to the value searched for.
parcels = [("anvil", 30), ("book", 5), ("clock", 8), ("drum", 12)]
parcels.sort(key=lambda parcel: parcel[1])
first_heavy = bisect_left(parcels, 10, key=lambda parcel: parcel[1])
print("first parcel of at least 10:", parcels[first_heavy])
