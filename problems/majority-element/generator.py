"""Seeded inputs for majority-element, shaped so every approach shows its declared growth.

The majority value fills between n/2 + 1 and about 0.6 n positions; the rest hold values
from a random pool of other values, so small inputs repeat minority values often. Between
half and all of the minority elements come first, before any copy of the majority value, and
the remaining elements are shuffled.

Counting every candidate then performs a full scan for each leading minority element, about
n^2/5 to n^2/2 comparisons at every seed, while the linear approaches always read the whole
array (or, for the early-exit hash map, at least half of it).
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 5 * 10**4
VALUE_LIMIT = 10**9


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    majority_count = min(length, length // 2 + 1 + rng.randrange(max(1, length // 10)))
    minority_count = length - majority_count
    majority = rng.randint(-VALUE_LIMIT, VALUE_LIMIT)

    pool_size = rng.randint(1, max(1, minority_count))
    pool = [
        value
        for value in rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), pool_size + 1)
        if value != majority
    ][:pool_size]
    minority = [rng.choice(pool) for _ in range(minority_count)]

    leading = rng.randint(minority_count // 2, minority_count)
    rest = minority[leading:] + [majority] * majority_count
    rng.shuffle(rest)
    return {"nums": minority[:leading] + rest}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    counts: dict[int, int] = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
    assert max(counts.values()) > len(nums) // 2, "no value occurs more than n/2 times"
