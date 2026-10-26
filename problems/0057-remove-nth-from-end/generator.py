"""Seeded inputs for remove-nth-from-end: a list of `n` nodes and a position from the end.

The generator's size `n` is the list length L (at least 1). The position to remove is the
tail with probability 1/4, the head with probability 1/4, and uniform otherwise, because the
two ends are where off-by-one mistakes and a missing dummy node show up.
"""

import random

MIN_NODES = 1
MAX_NODES = 10**5
VALUE_LIMIT = 10**4


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, MIN_NODES), MAX_NODES)
    roll = rng.random()
    if roll < 0.25:
        position = 1
    elif roll < 0.5:
        position = size
    else:
        position = rng.randint(1, size)
    values = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(size)]
    return {"head": values, "n": position}


def validate(case_input: dict) -> None:
    head, position = case_input["head"], case_input["n"]
    assert isinstance(head, list), "the input list must not have a cycle"
    assert MIN_NODES <= len(head) <= MAX_NODES, "node count out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in head), "value out of range"
    assert 1 <= position <= len(head), "n must name a node of the list"
