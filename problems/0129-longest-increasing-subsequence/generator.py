"""Seeded inputs for longest-increasing-subsequence.

`n` is the array length, clamped to 1..2500. Each input picks one shape: uniform values over
the full range, a narrow range with many duplicates, a nearly sorted array (a sorted array with
a few random swaps, so the answer is long and the top-down recursion goes deep), or a nearly
reversed one (short answers).
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 2500
VALUE_LIMIT = 10**4
NARROW_RANGE = 20


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    shape = rng.choice(("uniform", "duplicates", "nearly-sorted", "nearly-reversed"))
    if shape == "duplicates":
        nums = [rng.randint(-NARROW_RANGE, NARROW_RANGE) for _ in range(length)]
    else:
        nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(length)]
    if shape in ("nearly-sorted", "nearly-reversed"):
        nums.sort(reverse=shape == "nearly-reversed")
        for _ in range(max(1, length // 20)):
            i, j = rng.randrange(length), rng.randrange(length)
            nums[i], nums[j] = nums[j], nums[i]
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
