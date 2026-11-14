"""Seeded inputs for merge-k-sorted-lists: `n` nodes spread over k sorted lists.

From n = 100 on there are k = n / 10 lists, so merging them into the result one at a time
costs about k * n / 2 node steps (quadratic in n) while the heap and the pairwise rounds
stay at n log k. Below 100 nodes, k is uniform between 1 and n, so the oracle also sees one
long list, many short ones and everything between. The nodes are split among the lists by
random cut points, so some lists are empty. Values come from a narrow or a wide range.
"""

import random

MAX_TOTAL_NODES = 10**4
MAX_LISTS = 10**4
MAX_LIST_NODES = 500
VALUE_LIMIT = 10**4
FIXED_RATIO_FROM = 100
NODES_PER_LIST = 10


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 1), MAX_TOTAL_NODES)
    if total >= FIXED_RATIO_FROM:
        count = total // NODES_PER_LIST
    else:
        count = rng.randint(1, total)
    cuts = sorted(rng.randint(0, total) for _ in range(count - 1))
    sizes = [high - low for low, high in zip([0, *cuts], [*cuts, total], strict=True)]
    limit = rng.choice((10, VALUE_LIMIT))
    lists = [sorted(rng.randint(-limit, limit) for _ in range(size)) for size in sizes]
    return {"lists": lists}


def validate(case_input: dict) -> None:
    lists = case_input["lists"]
    assert len(lists) <= MAX_LISTS, "too many lists"
    assert sum(len(values) for values in lists) <= MAX_TOTAL_NODES, "too many nodes"
    for values in lists:
        assert isinstance(values, list), "a list must not have a cycle"
        assert len(values) <= MAX_LIST_NODES, "a list is too long"
        assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in values), "value out of range"
        assert values == sorted(values), "a list is not sorted"
