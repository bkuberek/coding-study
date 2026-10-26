"""Seeded inputs for kth-largest-element: `n` values and a rank `k` between 1 and n.

Below 100 values, which covers the oracle's inputs, most inputs are random over the full value
range, a fifth use only a handful of distinct values (long runs of equal values break two-way
partitions), and a fifth are sorted ascending (which breaks a quickselect that always picks the
first or last element as its pivot); `k` is uniform between 1 and n.

From 100 values on, the sizes the ladder times, every input is random over the full range and
`k` is n/2, the median. The heap of the k largest then holds n/2 values at every seed, so its
O(n log k) work does not swing between almost nothing (k = 1) and a full heap (k = n) from one
size of the ladder to the next.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**4
FEW_DISTINCT = 3
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= UNIFORM_FROM:
        nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(length)]
        return {"nums": nums, "k": length // 2}
    roll = rng.random()
    limit = FEW_DISTINCT if roll < 0.2 else VALUE_LIMIT
    nums = [rng.randint(-limit, limit) for _ in range(length)]
    if roll > 0.8:
        nums.sort()
    return {"nums": nums, "k": rng.randint(1, length)}


def validate(case_input: dict) -> None:
    nums, k = case_input["nums"], case_input["k"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert 1 <= k <= len(nums), "k out of range"
