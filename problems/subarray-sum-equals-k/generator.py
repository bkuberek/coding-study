"""Seeded inputs for subarray-sum-equals-k.

`n` is the length of `nums`. The values come from a range picked per input (tiny, small or the
full range), so prefix sums repeat often in some inputs and rarely in others. `k` is usually
the sum of a random subarray, which guarantees at least one answer; one input in five uses
a random `k` instead, often with no answer at all. One input in ten is all zeros with
`k = 0`, where every subarray counts. Neither approach stops early, so the brute force does
n(n + 1)/2 additions on every input.
"""

import random

MAX_LENGTH = 2 * 10**4
VALUE_LIMIT = 1000
K_LIMIT = 10**7
VALUE_RANGES = [1, 3, 10, VALUE_LIMIT]
ZERO_SHARE = 0.1
RANDOM_K_SHARE = 0.2


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if rng.random() < ZERO_SHARE:
        return {"nums": [0] * length, "k": 0}
    limit = rng.choice(VALUE_RANGES)
    nums = [rng.randint(-limit, limit) for _ in range(length)]
    if rng.random() < RANDOM_K_SHARE:
        k = rng.randint(-limit * 4, limit * 4)
    else:
        start = rng.randrange(length)
        end = rng.randrange(start, length)
        k = sum(nums[start : end + 1])
    return {"nums": nums, "k": k}


def validate(case_input: dict) -> None:
    nums, k = case_input["nums"], case_input["k"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert -K_LIMIT <= k <= K_LIMIT, "k out of range"
