"""Seeded inputs for missing-number: the numbers 0 to n without one of them, shuffled.

`n` is the length of `nums`. The missing number is uniform over 0 to n, so it is sometimes
0 or n itself. The sum of 0 to n reaches 5 * 10^9 at the largest size, beyond a 32-bit int.
"""

import random

MAX_LENGTH = 10**5


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    missing = rng.randint(0, length)
    nums = [value for value in range(length + 1) if value != missing]
    rng.shuffle(nums)
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value <= len(nums) for value in nums), "value out of range"
    assert len(set(nums)) == len(nums), "values must be distinct"
