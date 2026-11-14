"""Seeded inputs for product-except-self: `n` values whose products always fit in 32 bits.

Most values are 1 or -1. Up to 40 positions get a magnitude from 2 to 30 with a random sign,
as long as the product of all magnitudes stays at most 2^31 - 1, so every product of any
selection of elements fits in a 32-bit signed integer, as the constraints promise. About 40%
of the inputs then get one or two zeros.

Every approach does the same work whatever the values: the brute force always performs about
n^2 multiplications, the others about 3n.
"""

import random

MIN_LENGTH = 2
MAX_LENGTH = 10**5
VALUE_LIMIT = 30
PRODUCT_LIMIT = 2**31 - 1
MAX_LARGE_VALUES = 40
ZERO_COUNTS = (0, 0, 0, 1, 1, 2)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    nums = [rng.choice((-1, 1)) for _ in range(length)]
    product = 1
    for position in rng.sample(range(length), min(length, rng.randint(0, MAX_LARGE_VALUES))):
        magnitude = rng.randint(2, VALUE_LIMIT)
        if product * magnitude > PRODUCT_LIMIT:
            break
        product *= magnitude
        nums[position] = magnitude * rng.choice((-1, 1))
    for position in rng.sample(range(length), min(length, rng.choice(ZERO_COUNTS))):
        nums[position] = 0
    return {"nums": nums}


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    product = 1
    for value in nums:
        if value != 0:
            product *= abs(value)
    assert product <= PRODUCT_LIMIT, "a product of some elements overflows 32 bits"
