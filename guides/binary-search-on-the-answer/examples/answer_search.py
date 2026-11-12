"""Binary search on the answer: no sorted array, only a yes/no check that is monotone in the answer.

Sensors go on posts along a fence. Place k of them so that the closest two are as far apart as possible.
"""

from bisect import bisect_left
from collections.abc import Callable
from itertools import combinations


def first_true(lo: int, hi: int, is_true: Callable[[int], bool]) -> int:
    """The smallest i in [lo, hi) with is_true(i), or hi when there is none."""
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if is_true(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


posts = [0, 3, 4, 7, 11, 12, 18, 20, 25]  # metres along the fence, sorted
k = 4


def fits(gap: int) -> bool:
    """Can k sensors stand on posts with every two at least gap apart? Greedy: each sensor on the
    first post far enough from the previous one, which leaves the most room for the rest."""
    count, last = 1, posts[0]
    for post in posts[1:]:
        if post - last >= gap:
            count, last = count + 1, post
    return count >= k


print("gap:  ", " ".join(f"{gap:2}" for gap in range(1, 13)))
print("fits: ", " ".join(" T" if fits(gap) else " F" for gap in range(1, 13)))

# fits is true, then false. The answer is the last true gap: one less than the first false one.
span = posts[-1] - posts[0]


def too_wide(gap: int) -> bool:
    print(f"  try gap {gap:2}: {'fits' if fits(gap) else 'too wide'}")
    return not fits(gap)


print(f"search the gaps 1..{span}:")
first_too_wide = first_true(1, span + 1, too_wide)
print("largest gap:", first_too_wide - 1)

# The same search with bisect: a range is a sequence whose elements are computed, not stored.
gaps = range(1, span + 2)
print("with bisect over a range:", gaps[bisect_left(gaps, True, key=lambda gap: not fits(gap))] - 1)

# Checking every choice of k posts agrees, at a cost that grows much faster.
best = max(min(b - a for a, b in zip(chosen, chosen[1:])) for chosen in combinations(posts, k))
print(f"every choice of {k} posts out of {len(posts)}: largest gap {best}")
