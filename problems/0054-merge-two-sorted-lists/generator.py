"""Seeded inputs for merge-two-sorted-lists: two sorted lists with `n` nodes in total.

The first list gets a uniformly random share of the `n` nodes (possibly none) and the second
list the rest. Values come from a randomly chosen spread (narrow, medium or the full range),
so some inputs are full of duplicates and ties across the lists, and others barely overlap.
The total is capped at 3000 nodes, the recursion depth the content rules allow, because the
recursive approach makes one call per merged node.
"""

import random

MAX_TOTAL_NODES = 3000
VALUE_LIMIT = 5000
SPREADS = (5, 100, VALUE_LIMIT)


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 0), MAX_TOTAL_NODES)
    first_size = rng.randint(0, total)
    spread = rng.choice(SPREADS)
    low = rng.randint(-VALUE_LIMIT, VALUE_LIMIT - spread)
    return {
        "list1": _sorted_values(rng, first_size, low, spread),
        "list2": _sorted_values(rng, total - first_size, low, spread),
    }


def _sorted_values(rng: random.Random, size: int, low: int, spread: int) -> list[int]:
    return sorted(rng.randint(low, low + spread) for _ in range(size))


def validate(case_input: dict) -> None:
    first, second = case_input["list1"], case_input["list2"]
    assert isinstance(first, list) and isinstance(second, list), "the lists must not have cycles"
    assert len(first) + len(second) <= MAX_TOTAL_NODES, "too many nodes"
    for values in (first, second):
        assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in values), "value out of range"
        assert values == sorted(values), "a list is not sorted"
