"""Seeded inputs for max-average-fixed-window.

`n` is the length of `nums`, and the window width is k = n // 2. From 100 values on, the sizes
the ladder times, every input is uniform over the full value range, so adding up every window
from scratch costs about n^2 / 4 steps at each seed and a sliding window about n.

Below 100 values, which covers the oracle's inputs, the width is uniform between 1 and n and
the values come from one of four families: the full range, a handful of small values, only
negative values (a best sum that starts at 0 would be wrong), or one repeated value.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**4
UNIFORM_FROM = 100
SMALL_VALUE = 3


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= UNIFORM_FROM:
        nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(length)]
        return {"nums": nums, "k": length // 2}
    family = rng.choice(("wide", "small", "negative", "constant"))
    if family == "wide":
        nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(length)]
    elif family == "small":
        nums = [rng.randint(-SMALL_VALUE, SMALL_VALUE) for _ in range(length)]
    elif family == "negative":
        nums = [rng.randint(-VALUE_LIMIT, -1) for _ in range(length)]
    else:
        nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT)] * length
    return {"nums": nums, "k": rng.randint(1, length)}


def validate(case_input: dict) -> None:
    nums, k = case_input["nums"], case_input["k"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert 1 <= k <= len(nums), "k out of range"
