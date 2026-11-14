"""Seeded inputs for lowest-common-ancestor.

The shape is random (each node fills a uniformly random empty child slot, so the expected
height is logarithmic) and the values are n distinct integers from [-10^9, 10^9] in random
positions, so the tree is not a search tree. `p` is a random node; `q` is the same node 15% of
the time, a random descendant of `p` 20% of the time (one is an ancestor of the other), and
otherwise any random node.
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
    values = rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), size)
    p = rng.randrange(size)
    roll = rng.random()
    if roll < 0.15:
        q = p
    elif roll < 0.35:
        q = rng.choice(_subtree(left, right, p))
    else:
        q = rng.randrange(size)
    if rng.random() < 0.5:
        p, q = q, p
    return {"root": _level_order(left, right, values), "p": values[p], "q": values[q]}


def validate(case_input: dict) -> None:
    root = case_input["root"]
    nodes = [value for value in root if value is not None]
    assert 1 <= len(nodes) <= MAX_NODES, "node count out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nodes), "value out of range"
    assert len(set(nodes)) == len(nodes), "values must be distinct"
    assert case_input["p"] in nodes and case_input["q"] in nodes, "p and q must be nodes of the tree"
    assert root[0] is not None and root[-1] is not None, "bad level-order encoding"
    assert _height(root) <= MAX_HEIGHT, "tree too tall"


def _subtree(left: list[int], right: list[int], top: int) -> list[int]:
    members = [top]
    for node in members:
        members.extend(child for child in (left[node], right[node]) if child != NO_CHILD)
    return members


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
