"""Seeded inputs for combination-sum within the stated constraints.

The target is n, capped at 40. Between 1 and 30 distinct candidates are drawn from [2, 40]
in random order. The constraints promise at most 150 combinations, so the generator counts
them with the classic "ways to make each sum" table and drops the smallest candidate (the
one that creates the most combinations) until the count is within the limit. One candidate
alone makes at most one combination, so this always terminates with a non-empty array.

That limit also caps the search: dropping the candidates that make many combinations keeps
the search small whatever the target, with a size that depends far more on the candidates a
seed draws than on n. The search is largest when the target cannot be reached at all, which
the limit allows. So odd
targets of 15 or more, which include every size of the ladder, get every even value from 2
to 40 as candidates, in ascending order: no combination reaches an odd target, the answer is
empty, and both approaches try every multiset of even values whose sum stays below it. Their
number grows like the partition numbers, faster than any polynomial in the target, and the
input is the same at every seed.
"""

import random

MIN_TARGET = 1
MAX_TARGET = 40
MIN_VALUE = 2
MAX_VALUE = 40
MAX_CANDIDATES = 30
MAX_COMBINATIONS = 150
UNREACHABLE_FROM = 15


def count_combinations(candidates: list[int], target: int) -> int:
    ways = [1] + [0] * target
    for value in candidates:
        for total in range(value, target + 1):
            ways[total] += ways[total - value]
    return ways[target]


def generate(rng: random.Random, n: int) -> dict:
    target = min(max(n, MIN_TARGET), MAX_TARGET)
    if target % 2 and target >= UNREACHABLE_FROM:
        return {"candidates": list(range(MIN_VALUE, MAX_VALUE + 1, 2)), "target": target}
    count = rng.randint(1, MAX_CANDIDATES)
    candidates = rng.sample(range(MIN_VALUE, MAX_VALUE + 1), count)
    while count_combinations(candidates, target) > MAX_COMBINATIONS:
        candidates.remove(min(candidates))
    return {"candidates": candidates, "target": target}


def validate(case_input: dict) -> None:
    candidates, target = case_input["candidates"], case_input["target"]
    assert 1 <= len(candidates) <= MAX_CANDIDATES, "candidate count out of range"
    assert all(MIN_VALUE <= value <= MAX_VALUE for value in candidates), "candidate out of range"
    assert len(set(candidates)) == len(candidates), "candidates must be distinct"
    assert MIN_TARGET <= target <= MAX_TARGET, "target out of range"
    assert count_combinations(candidates, target) <= MAX_COMBINATIONS, "too many combinations"
