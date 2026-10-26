"""Seeded inputs for first-missing-positive, shaped so the answer grows with `n`.

The array holds every value from 1 to `m`, with `m` between n/2 and n, except that in about
half of the inputs one value from the upper half of that range is left out. The remaining
positions hold noise: zero or negative values, values larger than `n`, and repeats of values
already present. Then the array is shuffled.

The answer is therefore at least about n/4, so trying 1, 2, 3, ... with a linear search each
costs on the order of n^2 comparisons at every seed, while the linear approaches visit each
position a constant number of times.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
GAP_PROBABILITY = 0.5


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    top = rng.randint((length + 1) // 2, length)
    nums = list(range(1, top + 1))
    if rng.random() < GAP_PROBABILITY:
        nums.remove(rng.randint((top + 1) // 2, top))
    present = nums[:]
    while len(nums) < length:
        nums.append(_noise(rng, length, present))
    rng.shuffle(nums)
    return {"nums": nums}


def _noise(rng: random.Random, length: int, present: list[int]) -> int:
    kind = rng.randrange(3)
    if kind == 0 or not present:
        return rng.randint(INT_MIN, 0)
    if kind == 1:
        return rng.randint(length + 1, INT_MAX)
    return rng.choice(present)


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(INT_MIN <= value <= INT_MAX for value in nums), "value out of range"
