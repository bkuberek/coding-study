"""Seeded inputs for max-product-subarray.

`n` is the array length, clamped to 1..20000. Values are drawn from -10..10, mostly +1 or -1 so
that zero-free runs stay long. The generator tracks the product of absolute values of the
current zero-free run and, whenever the next value would push it past 2^31 - 1, draws a 0 or a
+1/-1 instead. Every subarray product is then bounded by its run's product, as the constraints
promise.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 2 * 10**4
VALUE_LIMIT = 10
PRODUCT_LIMIT = 2**31 - 1
ZERO_SHARE = 0.03
UNIT_SHARE = 0.6


def _draw(rng: random.Random) -> int:
    roll = rng.random()
    if roll < ZERO_SHARE:
        return 0
    sign = rng.choice((-1, 1))
    if roll < ZERO_SHARE + UNIT_SHARE:
        return sign
    return sign * rng.randint(2, VALUE_LIMIT)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    nums: list[int] = []
    run_product = 1
    for _ in range(length):
        value = _draw(rng)
        if value != 0 and run_product * abs(value) > PRODUCT_LIMIT:
            value = rng.choice((0, -1, 1))
        run_product = 1 if value == 0 else run_product * abs(value)
        nums.append(value)
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    # The largest and smallest products of subarrays ending at each index, in exact arithmetic.
    largest = smallest = 1
    for value in nums:
        candidates = (value, largest * value, smallest * value)
        largest, smallest = max(candidates), min(candidates)
        assert -PRODUCT_LIMIT - 1 <= smallest <= largest <= PRODUCT_LIMIT, (
            "a subarray product does not fit in 32 bits"
        )
