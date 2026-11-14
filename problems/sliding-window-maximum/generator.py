"""Seeded inputs for sliding-window-maximum: wide windows over varied shapes.

The window width k is between n/8 and n/2, so scanning every window costs about
(n - k + 1) * k steps, which is between 7n^2/64 and n^2/4: quadratic at every seed.
Values follow random noise, a rising or falling trend (where the monotonic deque holds
many or few candidates), or a sawtooth, all within the constraints.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**4
SHAPES = ("noise", "rising", "falling", "sawtooth")


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    width = rng.randint(max(1, length // 8), max(1, length // 2))
    shape = rng.choice(SHAPES)
    nums = [_value(rng, shape, index, length) for index in range(length)]
    return {"nums": nums, "k": width}


def validate(case_input: dict) -> None:
    nums, width = case_input["nums"], case_input["k"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert 1 <= width <= len(nums), "k out of range"


def _value(rng: random.Random, shape: str, index: int, length: int) -> int:
    position = index / max(1, length - 1)
    if shape == "rising":
        base = 2 * position - 1
    elif shape == "falling":
        base = 1 - 2 * position
    elif shape == "sawtooth":
        base = 2 * ((index % 97) / 96) - 1
    else:
        return rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
    noisy = base * 0.9 * VALUE_LIMIT + rng.randint(-VALUE_LIMIT // 10, VALUE_LIMIT // 10)
    return max(-VALUE_LIMIT, min(VALUE_LIMIT, round(noisy)))
