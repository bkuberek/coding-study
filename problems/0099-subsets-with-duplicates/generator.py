"""Seeded inputs for subsets-with-duplicates: one value three times, one twice, the rest once.

The length is n, capped at the constraint of 10. The values are distinct random integers from
[-10, 10]; the first appears three times, the second twice and every other one once (shorter
arrays keep only the first one or two of those values), and the array is then shuffled. Runs
of two and three equal values both occur at every length, so skipping equal siblings is
exercised every time.

The shape is the same at every seed: an array of length n >= 5 has 4 * 3 * 2^(n - 5) distinct
subsets, three eighths of the 2^n subsets of distinct values, so both approaches grow like 2^n
from one size of the ladder to the next. Drawing the number of distinct values per seed would
let an array of one repeated value (n + 1 subsets) land on any size.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10
VALUE_LIMIT = 10
REPEATS = (3, 2)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    counts: list[int] = []
    left = length
    while left:
        count = min(left, REPEATS[len(counts)] if len(counts) < len(REPEATS) else 1)
        counts.append(count)
        left -= count
    values = rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), len(counts))
    nums = [value for value, count in zip(values, counts, strict=True) for _ in range(count)]
    rng.shuffle(nums)
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
