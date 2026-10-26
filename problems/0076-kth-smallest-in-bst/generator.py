"""Seeded inputs for kth-smallest-in-bst: random binary search trees and a random rank.

The shape is random (each node fills a uniformly random empty child slot, so the expected
height is logarithmic) and n distinct values from [-10^9, 10^9] are placed by an in-order
walk, which makes a valid binary search tree. `k` is 1 or n one time in ten each, otherwise
uniform in [1, n].
"""

import random
from collections import deque

MAX_NODES = 10**5
MAX_HEIGHT = 3000
VALUE_LIMIT = 10**9
NO_CHILD = -1


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES)
    left, right = _random_shape(rng, size)
    sorted_values = sorted(rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), size))
    values = [0] * size
    for rank, node in enumerate(_in_order(left, right)):
        values[node] = sorted_values[rank]
    roll = rng.random()
    k = 1 if roll < 0.1 else size if roll < 0.2 else rng.randint(1, size)
    return {"root": _level_order(left, right, values), "k": k}


def validate(case_input: dict) -> None:
    root, k = case_input["root"], case_input["k"]
    nodes = [value for value in root if value is not None]
    assert 1 <= len(nodes) <= MAX_NODES, "node count out of range"
    assert 1 <= k <= len(nodes), "k out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nodes), "value out of range"
    assert len(set(nodes)) == len(nodes), "values must be distinct"
    assert root[0] is not None and root[-1] is not None, "bad level-order encoding"
    assert _height(root) <= MAX_HEIGHT, "tree too tall"


def _in_order(left: list[int], right: list[int]) -> list[int]:
    order: list[int] = []
    stack: list[int] = []
    node = 0
    while stack or node != NO_CHILD:
        while node != NO_CHILD:
            stack.append(node)
            node = left[node]
        node = stack.pop()
        order.append(node)
        node = right[node]
    return order


def _random_shape(rng: random.Random, size: int) -> tuple[list[int], list[int]]:
    left = [NO_CHILD] * size
    right = [NO_CHILD] * size
    empty_slots = [(0, left), (0, right)]
    for node in range(1, size):
        pick = rng.randrange(len(empty_slots))
        parent, children = empty_slots[pick]
        empty_slots[pick] = empty_slots[-1]
        empty_slots.pop()
        children[parent] = node
        empty_slots.append((node, left))
        empty_slots.append((node, right))
    return left, right


def _level_order(left: list[int], right: list[int], values: list[int]) -> list[int | None]:
    encoded: list[int | None] = []
    queue = deque([0])
    while queue:
        node = queue.popleft()
        if node == NO_CHILD:
            encoded.append(None)
            continue
        encoded.append(values[node])
        queue.append(left[node])
        queue.append(right[node])
    while encoded and encoded[-1] is None:
        encoded.pop()
    return encoded


def _height(root: list[int | None]) -> int:
    """Height of a level-order encoded tree: after the root, tokens come in (left, right) pairs."""
    owner_depths = deque([1])
    height = 1
    for start in range(1, len(root), 2):
        assert owner_depths, "children listed under a missing node"
        depth = owner_depths.popleft() + 1
        for value in root[start : start + 2]:
            if value is not None:
                owner_depths.append(depth)
                height = max(height, depth)
    return height
