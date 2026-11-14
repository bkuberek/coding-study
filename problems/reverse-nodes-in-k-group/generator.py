"""Seeded inputs for reverse-nodes-in-k-group: a list of `n` nodes and a group size `k`.

`k` is 1, 2 or 3, a uniform value between 1 and n, or n itself, each with probability 1/5:
k = 1 leaves the list unchanged, k = n reverses all of it, and the others produce a mix of
full groups and a shorter tail that must stay in place. Values may repeat.
"""

import random

MIN_NODES = 1
MAX_NODES = 10**5
VALUE_LIMIT = 1000


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, MIN_NODES), MAX_NODES)
    choices = (1, min(2, size), min(3, size), rng.randint(1, size), size)
    k = rng.choice(choices)
    values = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(size)]
    return {"head": values, "k": k}


def validate(case_input: dict) -> None:
    head, k = case_input["head"], case_input["k"]
    assert isinstance(head, list), "the input list must not have a cycle"
    assert MIN_NODES <= len(head) <= MAX_NODES, "node count out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in head), "value out of range"
    assert 1 <= k <= len(head), "k out of range"
