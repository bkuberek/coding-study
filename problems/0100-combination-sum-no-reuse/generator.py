"""Seeded inputs for combination-sum-no-reuse within the stated constraints.

Up to WORST_CASE_MAX entries (the bench ladder), every input is the search's worst case: the
entries 1..n in random order, with the target their total capped at the target limit. Up to
seven entries (1 + 2 + ... + 7 = 28) every subset stays within the target, so the backtracking
visits all 2^n of them; at eight and nine entries it still visits nearly all of them.

Longer arrays have n entries, capped at 15, drawn from [1, top] with top random in [1, 30]:
a small top gives many repeated values, a large one few. The target is uniform in [1, 30],
so some inputs have no combination at all. The target limit caps their search, so it stops
growing as 2^n.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 15
MAX_VALUE = 30
MAX_TARGET = 30
WORST_CASE_MAX = 9


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length <= WORST_CASE_MAX:
        candidates = list(range(1, length + 1))
        rng.shuffle(candidates)
        return {"candidates": candidates, "target": min(sum(candidates), MAX_TARGET)}
    top = rng.randint(1, MAX_VALUE)
    candidates = [rng.randint(1, top) for _ in range(length)]
    return {"candidates": candidates, "target": rng.randint(1, MAX_TARGET)}


def validate(case_input: dict) -> None:
    candidates, target = case_input["candidates"], case_input["target"]
    assert MIN_LENGTH <= len(candidates) <= MAX_LENGTH, "length out of range"
    assert all(1 <= value <= MAX_VALUE for value in candidates), "candidate out of range"
    assert 1 <= target <= MAX_TARGET, "target out of range"
