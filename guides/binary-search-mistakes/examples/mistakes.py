"""Four ways a binary search goes wrong, each caught by running it: a loop that stops moving, a predicate
that is not monotone, floating-point midpoints that stop moving, and a one-character bug that a brute
force over small inputs finds at once."""

import math
from collections.abc import Callable
from itertools import combinations_with_replacement


def first_true(lo: int, hi: int, is_true: Callable[[int], bool]) -> int:
    """The smallest i in [lo, hi) with is_true(i), or hi: correct when is_true is monotone."""
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if is_true(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


# 1. No progress: the largest k with k * k <= n, searched with lo = mid and a midpoint rounded down.
def isqrt_stuck(n: int, max_steps: int = 7) -> int | None:
    lo, hi = 0, n
    for _ in range(max_steps):
        if lo >= hi:
            return lo
        mid = lo + (hi - lo) // 2  # rounds down, so mid == lo once hi == lo + 1
        print(f"  lo {lo:2}  hi {hi:2}  mid {mid}  {mid} * {mid} = {mid * mid}")
        if mid * mid <= n:
            lo = mid  # keeps mid: nothing changes when mid == lo
        else:
            hi = mid - 1
    return None  # gave up; without the step limit the loop would never end


def isqrt_round_up(n: int) -> int:
    lo, hi = 0, n
    while lo < hi:
        mid = lo + (hi - lo + 1) // 2  # rounds up, so mid > lo and lo = mid always moves
        if mid * mid <= n:
            lo = mid
        else:
            hi = mid - 1
    return lo


def isqrt_first_false(n: int) -> int:
    return first_true(0, n + 1, lambda k: k * k > n) - 1  # the first k that is too big, minus one


print("largest k with k * k <= 10, using lo = mid and a midpoint rounded down:")
print("  ->", isqrt_stuck(10))
fixed = all(isqrt_round_up(n) == isqrt_first_false(n) == math.isqrt(n) for n in range(2000))
print("both fixes match math.isqrt for 0..1999:", fixed)
big = 10**40 + 12345
print("and for 10**40 + 12345:", isqrt_round_up(big) == isqrt_first_false(big) == math.isqrt(big))

# 2. Predicates that are not monotone: first_true finds *a* switch from F to T, not the first T.
readings = [7, 3, 9, 4, 8, 12, 15]  # not sorted
print("readings >= 8:  ", " ".join("T" if r >= 8 else "F" for r in readings))
print("  first_true says", first_true(0, len(readings), lambda i: readings[i] >= 8), "but the first T is at 2")
ages = [1, 3, 5, 5, 7, 9]  # sorted, but equality is still not monotone
print("ages == 3:      ", " ".join("T" if a == 3 else "F" for a in ages))
print("  first_true says", first_true(0, len(ages), lambda i: ages[i] == 3), "(none) but 3 is at 1")
print("  ages >= 3 finds", first_true(0, len(ages), lambda i: ages[i] >= 3), "then one equality check")


# 3. Real numbers: near 1e16 neighbouring doubles are 2 apart, so the midpoint can equal an end.
def bisect_real(
    lo: float, hi: float, is_true: Callable[[float], bool], eps: float, max_steps: int
) -> tuple[int, float]:
    steps = 0
    while hi - lo > eps and steps < max_steps:
        mid = (lo + hi) / 2
        if is_true(mid):
            hi = mid
        else:
            lo = mid
        steps += 1
    return steps, hi - lo


def bisect_until_stuck(lo: float, hi: float, is_true: Callable[[float], bool]) -> tuple[int, float]:
    steps = 0
    while True:
        mid = (lo + hi) / 2
        if not lo < mid < hi:  # no double strictly between: the interval cannot shrink any more
            return steps, hi - lo
        if is_true(mid):
            hi = mid
        else:
            lo = mid
        steps += 1


target = 1e16 + 2
print("math.ulp(1e16) =", math.ulp(1e16))
print("stop when hi - lo <= 1e-9: (steps, gap) =", bisect_real(0.0, target, lambda x: x >= target, 1e-9, 2000))
print("stop when no midpoint is left: (steps, gap) =", bisect_until_stuck(0.0, target, lambda x: x >= target))


# 4. A brute force over every small input finds a one-character bug in an upper bound.
def upper_bound_buggy(items: list[int], x: int) -> int:
    return first_true(0, len(items), lambda i: items[i] >= x)  # should be >


def upper_bound_spec(items: list[int], x: int) -> int:
    return sum(1 for value in items if value <= x)  # in a sorted array, that count is the upper bound


cases = [
    (list(items), x)
    for length in range(5)
    for items in combinations_with_replacement(range(3), length)  # every sorted array over 0, 1, 2
    for x in range(-1, 4)
]
failures = [(items, x) for items, x in cases if upper_bound_buggy(items, x) != upper_bound_spec(items, x)]
items, x = failures[0]
print(f"{len(cases)} cases, {len(failures)} failures; the first: items {items}, x {x}:", end=" ")
print(f"got {upper_bound_buggy(items, x)}, expected {upper_bound_spec(items, x)}")
