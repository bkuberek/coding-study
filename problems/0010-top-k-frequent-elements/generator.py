"""Seeded inputs for top-k-frequent-elements with a unique answer.

`k` is between 1 and min(10, n/4). Each of the `k` answer values occurs at least 3 times;
every other value occurs once or twice, so the k-th highest count is strictly greater than the
next one and the answer is unique, as the constraints promise. A random share of the array
goes to the other values (about 2n/3 distinct values at most, and never more than the value
range allows); the rest is spread over the answer values. The array is shuffled.

With many distinct values, sorting them by count grows like n log n, while the heap (k <= 10)
and the buckets stay linear.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**4
MAX_K = 10
TOP_MIN_COUNT = 3
SMALL_LENGTH = 4


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length < SMALL_LENGTH:
        value = rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
        return {"nums": [value] * length, "k": 1}

    k = rng.randint(1, min(MAX_K, length // SMALL_LENGTH))
    distinct_limit = 2 * VALUE_LIMIT + 1
    other_budget = rng.randint(0, length - TOP_MIN_COUNT * k)
    other_counts: list[int] = []
    while other_budget > 0 and len(other_counts) + k < distinct_limit:
        count = min(other_budget, rng.randint(1, 2))
        other_counts.append(count)
        other_budget -= count

    top_counts = [TOP_MIN_COUNT] * k
    for _ in range(length - TOP_MIN_COUNT * k - sum(other_counts)):
        top_counts[rng.randrange(k)] += 1

    values = rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), k + len(other_counts))
    nums = [
        value
        for value, count in zip(values, top_counts + other_counts, strict=True)
        for _ in range(count)
    ]
    rng.shuffle(nums)
    return {"nums": nums, "k": k}


def validate(case_input: dict) -> None:
    nums, k = case_input["nums"], case_input["k"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    counts: dict[int, int] = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
    assert 1 <= k <= len(counts), "k out of range"
    ordered = sorted(counts.values(), reverse=True)
    assert k == len(ordered) or ordered[k - 1] > ordered[k], "the answer is not unique"
