"""Seeded inputs for diameter-binary-tree: random shapes with logarithmic expected height.

Each new node fills a uniformly random empty child slot of the tree built so far, so the
expected height grows like log n. For small trees (at most 50 nodes, the oracle sizes), one
input in four is a random path instead, whose diameter is the whole tree. Values are random
and may repeat; the diameter never looks at them.
"""

import random
from collections import deque

MAX_NODES = 10**5
MAX_HEIGHT = 3000
VALUE_LIMIT = 10**4
NO_CHILD = -1
SMALL_TREE = 50
PATH_PROBABILITY = 0.25


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES)
    if size <= SMALL_TREE and rng.random() < PATH_PROBABILITY:
        left, right = _random_path(rng, size)
    else:
        left, right = _random_shape(rng, size)
    values = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(size)]
    return {"root": _level_order(left, right, values)}


def validate(case_input: dict) -> None:
    root = case_input["root"]
    nodes = [value for value in root if value is not None]
    assert 1 <= len(nodes) <= MAX_NODES, "node count out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nodes), "value out of range"
    assert root[0] is not None, "a non-empty tree needs a root value"
    assert root[-1] is not None, "trailing nulls must be trimmed"
    assert _height(root) <= MAX_HEIGHT, "tree too tall"


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


def _random_path(rng: random.Random, size: int) -> tuple[list[int], list[int]]:
    left = [NO_CHILD] * size
    right = [NO_CHILD] * size
    for node in range(1, size):
        children = left if rng.random() < 0.5 else right
        children[node - 1] = node
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
