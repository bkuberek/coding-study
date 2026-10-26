"""Seeded inputs for linked-list-cycle: a list of `n` nodes, cyclic about half the time.

A cyclic list is written as `{"values": [...], "cycle_at": k}`: the tail links back to node
`k`. Below 100 nodes, which covers the oracle's inputs, `k` is uniform, so the loop may be the
whole list, a self-loop at the tail, or anything in between. From 100 nodes on, the sizes the
ladder times, `k` is the middle node: fast and slow pointers then meet after about n/2 steps,
as many as they take to run off the end of a list without a loop, and a visited set records
all n nodes either way, so the work does not depend on whether a seed draws a loop. Values
come from a narrow range half the time, so repeated values are common and a solution that
compares values instead of node identities fails.
"""

import random

MAX_NODES = 10**5
VALUE_LIMIT = 10**5
NARROW_LIMIT = 3
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 0), MAX_NODES)
    limit = NARROW_LIMIT if rng.random() < 0.5 else VALUE_LIMIT
    values = [rng.randint(-limit, limit) for _ in range(size)]
    if size and rng.random() < 0.5:
        return {"head": {"values": values, "cycle_at": _cycle_start(rng, size)}}
    return {"head": values}


def validate(case_input: dict) -> None:
    head = case_input["head"]
    values = head["values"] if isinstance(head, dict) else head
    assert len(values) <= MAX_NODES, "too many nodes"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in values), "value out of range"
    if isinstance(head, dict):
        assert 0 <= head["cycle_at"] < len(values), "cycle_at must index a node"


def _cycle_start(rng: random.Random, size: int) -> int:
    return size // 2 if size >= UNIFORM_FROM else rng.randrange(size)
