"""Seeded inputs for count-smaller-after-self.

`n` is the length of `nums`. Up to 30 values (the sizes of the oracle cross-check), the values
come from a range picked per input, from a handful of distinct values (many duplicates, so
strictness matters) to the full range of +-10^9. Longer inputs all have the same make-up, so
every ladder size costs the same per element: values drawn from the full range (so the tree
must work on compressed ranks), and every other position, on average, a copy of an earlier
value (so duplicates stay common). Comparing every pair costs n(n - 1)/2 steps; both
tree-based approaches cost O(n log n).
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
SMALL_LENGTH = 30
VALUE_RANGES = [3, 100, 10**5, VALUE_LIMIT]
COPY_SHARE = 0.5


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length <= SMALL_LENGTH:
        limit = rng.choice(VALUE_RANGES)
        return {"nums": [rng.randint(-limit, limit) for _ in range(length)]}
    nums: list[int] = []
    for _ in range(length):
        if nums and rng.random() < COPY_SHARE:
            nums.append(rng.choice(nums))
        else:
            nums.append(rng.randint(-VALUE_LIMIT, VALUE_LIMIT))
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
