"""Seeded inputs for reorder-list: a list of `n` random values (at least one node).

Values may repeat, so a solution must move nodes by position, never by value. The walk to the
tail for every move does about n^2 / 4 node steps, which is why the largest generated case
stays at 10^4 nodes.
"""

import random

MIN_NODES = 1
MAX_NODES = 5 * 10**4
VALUE_LIMIT = 1000


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, MIN_NODES), MAX_NODES)
    return {"head": [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(size)]}


def validate(case_input: dict) -> None:
    head = case_input["head"]
    assert isinstance(head, list), "the input list must not have a cycle"
    assert MIN_NODES <= len(head) <= MAX_NODES, "node count out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in head), "value out of range"
