"""Seeded inputs for last-stone-weight: `n` stone weights.

Most inputs draw weights uniformly from the full range. Below 100 stones, which covers the
oracle's inputs, a fifth of them draw from only a few distinct weights instead, so equal
stones meet often and destroy each other; from 100 stones on, which covers the sizes the
ladder times, every input draws from the full range.

Every smash removes at least one stone, so there are at most n - 1 rounds; re-sorting before
each of them is what makes the brute force slow. A round leaves a stone behind only when the
heaviest stone is unique, and that stone is lighter than the heaviest, so the heaviest weight
drops with every such round: at most 1000 of them insert a stone, however large n is. Past
about 1000 stones the share of such rounds therefore falls, and more of the brute force's
sorts find the list already sorted instead of sorted but for the one new stone. Both cost a
linear pass with the adaptive library sorts, but a sorted list is cheaper per element, so the
brute force's time per n^2 drifts down by about 2 times between 1000 and 10^4 stones.

The ladder starts at 300 stones: at 100, Rust's brute force spends most of a round on the
fixed cost of the round itself (two pops, a push and a sort call on about 50 values), a
lower-order O(n) term over the whole game that a fixed per-call cost cannot stand for, and the
drift against n^2 reached the 4x tolerance.
"""

import random

MIN_STONES = 1
MAX_STONES = 10**4
MAX_WEIGHT = 1000
FEW_WEIGHTS = (1, 2, 3, 500, 1000)
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_STONES), MAX_STONES)
    if rng.random() < 0.2 and count < UNIFORM_FROM:
        stones = [rng.choice(FEW_WEIGHTS) for _ in range(count)]
    else:
        stones = [rng.randint(1, MAX_WEIGHT) for _ in range(count)]
    return {"stones": stones}


def validate(case_input: dict) -> None:
    stones = case_input["stones"]
    assert MIN_STONES <= len(stones) <= MAX_STONES, "stone count out of range"
    assert all(1 <= weight <= MAX_WEIGHT for weight in stones), "weight out of range"
