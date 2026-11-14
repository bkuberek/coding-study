"""Seeded inputs for two-sum-sorted: a sorted array with exactly one valid pair.

The array holds n - 1 distinct even numbers and one odd number, in ascending order. The
target is odd, so a valid pair must combine the odd number with one even number, and
only one even number completes the sum: the answer is unique, as the statement promises.

The earlier element of the pair sits between positions n/20 and n/10 and the later one
in the back half. Checking every pair then performs between about n^2/20 and n^2/10
checks, a binary search per element performs about (n/10) log n steps, and the two
pointers walk at most n steps: each approach shows its growth at every seed.
"""

import random

MIN_LENGTH = 2
MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
TARGET_LIMIT = 10**9
HALF_RANGE = 2 * 10**8


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    evens = sorted(2 * v for v in rng.sample(range(-HALF_RANGE, HALF_RANGE), length - 1))
    front = rng.randint(length // 20, length // 10)
    back = rng.randint(max(length // 2, front + 1), length - 1)
    if rng.random() < 0.5:
        odd_index, odd = front, evens[front - 1] + 1 if front > 0 else evens[0] - 1
        partner = evens[back - 1]
    else:
        odd_index, odd = back, evens[back - 1] + 1
        partner = evens[front]
    numbers = evens[:odd_index] + [odd] + evens[odd_index:]
    return {"numbers": numbers, "target": odd + partner}


def validate(case_input: dict) -> None:
    numbers, target = case_input["numbers"], case_input["target"]
    assert MIN_LENGTH <= len(numbers) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in numbers), "value out of range"
    assert -TARGET_LIMIT <= target <= TARGET_LIMIT, "target out of range"
    assert all(a <= b for a, b in zip(numbers, numbers[1:])), "numbers must be sorted"
    assert _pair_count(numbers, target) == 1, "there must be exactly one valid pair"


def _pair_count(numbers: list[int], target: int) -> int:
    counts: dict[int, int] = {}
    for value in numbers:
        counts[value] = counts.get(value, 0) + 1
    pairs = 0
    for value, count in counts.items():
        partner = target - value
        if partner == value:
            pairs += count * (count - 1) // 2
        elif value < partner:
            pairs += count * counts.get(partner, 0)
    return pairs
