"""Seeded inputs for longest-consecutive-sequence: `n` values made of scattered runs.

Runs of random length (up to about n/20, at least 1) start at random places in the value
range, so runs rarely touch, but occasional merges are fine because expected values come
from a reference. About a tenth of the positions are then overwritten with copies of other
values, which adds repeats and sometimes breaks a run. Finally the array is shuffled.

Linear membership checks scan about n/2 to n elements for each value at every seed, so the
brute force grows with n^2 whatever the run structure; the hash set stays linear.
"""

import random

MIN_LENGTH = 0
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
REPEAT_FRACTION = 10


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    longest_allowed = max(1, length // 20)
    nums: list[int] = []
    while len(nums) < length:
        run_length = min(rng.randint(1, longest_allowed), length - len(nums))
        start = rng.randint(-VALUE_LIMIT, VALUE_LIMIT - run_length + 1)
        nums.extend(range(start, start + run_length))
    for _ in range(length // REPEAT_FRACTION):
        nums[rng.randrange(length)] = rng.choice(nums)
    rng.shuffle(nums)
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
