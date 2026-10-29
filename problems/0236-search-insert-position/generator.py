"""Seeded inputs for search-insert-position.

n distinct values sorted ascending. From 31 values on they are drawn from [-10^9, 10^9];
at oracle sizes (30 or fewer) from [-50, 50], with targets from [-55, 55], so targets below
the first value, above the last one and between neighbors all occur. Half of the targets are
values of the array, the rest are uniform over the range. Counting the smaller values reads
the whole array at every seed; binary search reads about log2 n of them.
"""

import random
from itertools import pairwise

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
SMALL_UP_TO = 30
SMALL_LIMIT = 50
SMALL_TARGET_LIMIT = 55


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length <= SMALL_UP_TO:
        limit, target_limit = SMALL_LIMIT, SMALL_TARGET_LIMIT
    else:
        limit, target_limit = VALUE_LIMIT, VALUE_LIMIT
    nums = sorted(rng.sample(range(-limit, limit + 1), length))
    target = rng.choice(nums) if rng.random() < 0.5 else rng.randint(-target_limit, target_limit)
    return {"nums": nums, "target": target}


def validate(case_input: dict) -> None:
    nums, target = case_input["nums"], case_input["target"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert all(earlier < later for earlier, later in pairwise(nums)), (
        "values must strictly increase"
    )
    assert -VALUE_LIMIT <= target <= VALUE_LIMIT, "target out of range"
