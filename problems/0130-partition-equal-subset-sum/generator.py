"""Seeded inputs for partition-equal-subset-sum.

`n` is the array length, clamped to 1..200, with values in 1..100, so the target (half the
total) grows linearly with `n`. Each input picks one shape: uniform values (an odd total is a
quick `false`; an even total is usually splittable), small values only, or one dominant value
of 100 with small values whose sum stays below it, which gives an even total that cannot be
split whenever the small values sum to less than 100.

From HARD_FROM values on (the bench ladder), every input is a worst case instead: an even
total that cannot be split, so no approach stops early. Every value is a multiple of 4 and
the total is 4 times an odd number, so half the total is 2 more than a multiple of 4, which
no subset of multiples of 4 reaches; the tables fill every cell and the memo explores every
reachable (index, remaining) pair, about n * t / 4 of them.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 200
MAX_VALUE = 100
SMALL_VALUE = 10
HARD_FROM = 25
HARD_STEP = 4


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= HARD_FROM:
        return {"nums": _unsplittable(rng, length)}
    shape = rng.choice(("uniform", "uniform", "small", "dominant"))
    if shape == "dominant" and length <= MAX_VALUE // SMALL_VALUE:
        nums = [MAX_VALUE] + [rng.randint(1, SMALL_VALUE) for _ in range(length - 1)]
        if sum(nums) % 2 == 1:
            nums[-1] = nums[-1] + 1 if nums[-1] < SMALL_VALUE else nums[-1] - 1
        rng.shuffle(nums)
    elif shape == "small":
        nums = [rng.randint(1, SMALL_VALUE) for _ in range(length)]
    else:
        nums = [rng.randint(1, MAX_VALUE) for _ in range(length)]
    return {"nums": nums}


def _unsplittable(rng: random.Random, length: int) -> list[int]:
    nums = [HARD_STEP * rng.randint(1, MAX_VALUE // HARD_STEP) for _ in range(length)]
    if sum(nums) // HARD_STEP % 2 == 0:
        # Moving one value by 4 makes the total 4 times an odd number.
        i = rng.randrange(length)
        nums[i] += HARD_STEP if nums[i] < MAX_VALUE else -HARD_STEP
    return nums


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(1 <= value <= MAX_VALUE for value in nums), "value out of range"
