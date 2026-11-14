"""Seeded inputs for sum-of-subarray-minimums: arrays with every kind of tie structure.

Shapes are uniform values over the whole range, values from a tiny range (so equal minimums
are everywhere), ascending and descending runs, and a valley. Every shape stresses the stack
differently, while the brute force always visits all n (n + 1) / 2 subarrays. From a few
hundred elements on, the sum exceeds the modulus, so the reduction is exercised too.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 3 * 10**4
MAX_VALUE = 3 * 10**4
FEW_VALUES = 5
SHAPES = ("uniform", "few", "ascending", "descending", "valley")


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    shape = rng.choice(SHAPES)
    high = FEW_VALUES if shape == "few" else MAX_VALUE
    arr = [rng.randint(1, high) for _ in range(length)]
    if shape == "ascending":
        arr.sort()
    elif shape == "descending":
        arr.sort(reverse=True)
    elif shape == "valley":
        arr.sort(reverse=True)
        middle = length // 2
        arr = arr[:middle] + sorted(arr[middle:])
    return {"arr": arr}


def validate(case_input: dict) -> None:
    arr = case_input["arr"]
    assert MIN_LENGTH <= len(arr) <= MAX_LENGTH, "length out of range"
    assert all(1 <= value <= MAX_VALUE for value in arr), "value out of range"
