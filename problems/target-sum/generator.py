"""Seeded inputs for target-sum: n values (at most 20) whose total is at most 1000.

Below UNIFORM_FROM values the inputs vary. On most seeds the total is between 500 and 1000,
split at random among the values; on the rest it is at most 50, so values are tiny and zeros
are common (each zero doubles the count). Half of the targets are the total of a random sign
assignment, so the answer is at least 1; the others are drawn from [-1000, 1000] and are often
unreachable.

From UNIFORM_FROM values on (the bench ladder), every input has one shape: values drawn from
[1, 10], so the total s grows in proportion to n, and the target is s mod 2, the most balanced
split. Nothing exits early: backtracking visits all 2^n assignments, the tables do
n * (2s + 1) and n * (s + 1) / 2 steps, and the memo reaches nearly every running total of
the right parity once the first few values are signed, so all three DP approaches grow as n^2.
"""

import random

MAX_LENGTH = 20
MAX_TOTAL = 1000
SMALL_TOTAL = 50
SMALL_SHARE = 0.2
TARGET_LIMIT = 1000
UNIFORM_FROM = 5
UNIFORM_MAX_VALUE = 10


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length >= UNIFORM_FROM:
        return _uniform(rng, length)
    return _varied(rng, length)


def _uniform(rng: random.Random, length: int) -> dict:
    nums = [rng.randint(1, UNIFORM_MAX_VALUE) for _ in range(length)]
    return {"nums": nums, "target": sum(nums) % 2}


def _varied(rng: random.Random, length: int) -> dict:
    if rng.random() < SMALL_SHARE:
        total = rng.randint(0, SMALL_TOTAL)
    else:
        total = rng.randint(MAX_TOTAL // 2, MAX_TOTAL)
    cuts = sorted(rng.randint(0, total) for _ in range(length - 1))
    nums = [high - low for low, high in zip([0, *cuts], [*cuts, total], strict=True)]
    if rng.random() < 0.5:
        target = sum(value if rng.random() < 0.5 else -value for value in nums)
    else:
        target = rng.randint(-TARGET_LIMIT, TARGET_LIMIT)
    return {"nums": nums, "target": target}


def validate(case_input: dict) -> None:
    nums, target = case_input["nums"], case_input["target"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value <= MAX_TOTAL for value in nums), "value out of range"
    assert sum(nums) <= MAX_TOTAL, "total out of range"
    assert -TARGET_LIMIT <= target <= TARGET_LIMIT, "target out of range"
