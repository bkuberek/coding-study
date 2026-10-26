"""Seeded inputs for {{title}} (docs/specs/problem-format.md#generated-cases-and-generatorpy).

TODO: how the inputs are built, and why they stay within the constraints.
"""

import random
from typing import Any

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**4


def generate(rng: random.Random, n: int) -> dict[str, Any]:
    length = min(max(n, 1), MAX_LENGTH)
    nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(length)]
    return {"nums": nums, "k": rng.randint(1, length)}


def validate(case_input: dict[str, Any]) -> None:
    nums: list[int] = case_input["nums"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
