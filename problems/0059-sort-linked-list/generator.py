"""Seeded inputs for sort-linked-list: `n` values in one of several orders.

Below 100 values, which covers the oracle's inputs, half of the inputs are in random order
over the full value range. The rest are split between a random order over only a few distinct
values (many ties), ascending order and descending order, because already sorted runs are
where merge-step and split mistakes show up.

From 100 values on, the sizes the ladder times, every input is in random order over the full
range. Insertion sort walks the sorted prefix from its head, so its work depends on the order:
about n^2 / 2 steps on ascending input, n^2 / 4 on random input and n on descending input. One
order at every seed keeps it quadratic along the whole ladder.
"""

import random

MAX_NODES = 5 * 10**4
VALUE_LIMIT = 10**5
FEW_DISTINCT = 5
ORDERS = ("random", "random", "random", "random", "few-distinct", "ascending", "descending")
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 0), MAX_NODES)
    order = rng.choice(ORDERS)
    if size >= UNIFORM_FROM:
        order = "random"
    limit = FEW_DISTINCT if order == "few-distinct" else VALUE_LIMIT
    values = [rng.randint(-limit, limit) for _ in range(size)]
    if order == "ascending":
        values.sort()
    elif order == "descending":
        values.sort(reverse=True)
    return {"head": values}


def validate(case_input: dict) -> None:
    head = case_input["head"]
    assert isinstance(head, list), "the input list must not have a cycle"
    assert len(head) <= MAX_NODES, "too many nodes"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in head), "value out of range"
