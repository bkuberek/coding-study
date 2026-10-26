"""Seeded inputs for reverse-linked-list: a list of `n` random values.

The length is capped at 3000 nodes, the recursion depth the content rules allow, because the
recursive approach makes one call per node. Values may repeat; reversal never compares them.
"""

import random

MAX_NODES = 3000
VALUE_LIMIT = 5000


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 0), MAX_NODES)
    return {"head": [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(size)]}


def validate(case_input: dict) -> None:
    head = case_input["head"]
    assert isinstance(head, list), "the input list must not have a cycle"
    assert len(head) <= MAX_NODES, "too many nodes"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in head), "value out of range"
