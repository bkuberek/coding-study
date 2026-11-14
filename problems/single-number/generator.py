"""Seeded inputs for single-number: (n - 1) / 2 distinct pairs plus one lonely value, shuffled.

`n` is the length of `nums`, rounded down to an odd number (at least 1). All values are
distinct 32-bit signed integers, drawn over the whole range so negative values and the
sign bit take part in the XOR. Both approaches make one pass.
"""

import random

MAX_LENGTH = 3 * 10**5
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length % 2 == 0:
        length -= 1
    distinct = rng.sample(range(INT_MIN, INT_MAX + 1), length // 2 + 1)
    lonely, paired = distinct[0], distinct[1:]
    nums = [lonely] + paired + paired
    rng.shuffle(nums)
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert 1 <= len(nums) <= MAX_LENGTH and len(nums) % 2 == 1, "length must be odd and in range"
    assert all(INT_MIN <= value <= INT_MAX for value in nums), "value out of range"
    counts: dict[int, int] = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
    singles = [value for value, count in counts.items() if count == 1]
    assert len(singles) == 1, "exactly one value must occur once"
    assert all(count in (1, 2) for count in counts.values()), "other values must occur twice"
