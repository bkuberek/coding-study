"""Seeded inputs for two-sum: exactly one valid pair, placed to make the work predictable.

The array holds n - 1 distinct even numbers and one odd number. The target is odd, so a
valid pair must combine the odd number with one even number, and only one even number
completes the sum: the answer is unique, as the statement guarantees.

The earlier element of the pair sits between positions n/20 and n/10 and the later one in
the back half. A scan over every pair then performs between about n^2/20 and n^2/10 checks
(quadratic at every seed), while a one-pass hash map reads at least half of the array
(linear at every seed).
"""

import random
from collections import Counter

MIN_LENGTH = 2
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
EVEN_HALF_RANGE = 4 * 10**8
ODD_HALF_RANGE = 10**8


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    evens = [2 * v for v in rng.sample(range(-EVEN_HALF_RANGE, EVEN_HALF_RANGE), length - 1)]
    partner = evens.pop(rng.randrange(length - 1))
    odd = 2 * rng.randrange(-ODD_HALF_RANGE, ODD_HALF_RANGE) + 1
    first, second = (odd, partner) if rng.random() < 0.5 else (partner, odd)

    first_index = rng.randint(length // 20, length // 10)
    second_index = rng.randint(max(length // 2, first_index + 1), length - 1)
    fillers = iter(evens)
    nums = [
        first if index == first_index else second if index == second_index else next(fillers)
        for index in range(length)
    ]
    return {"nums": nums, "target": odd + partner}


def validate(case_input: dict) -> None:
    nums, target = case_input["nums"], case_input["target"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert -VALUE_LIMIT <= target <= VALUE_LIMIT, "target out of range"
    assert _pair_count(nums, target) == 1, "there must be exactly one valid pair"


def _pair_count(nums: list[int], target: int) -> int:
    counts = Counter(nums)
    pairs = 0
    for value, count in counts.items():
        partner = target - value
        if partner == value:
            pairs += count * (count - 1) // 2
        elif value < partner:
            pairs += count * counts[partner]
    return pairs
