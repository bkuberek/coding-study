"""Seeded inputs for validate-bst: random binary search trees, some of them corrupted.

The shape is random (each node fills a uniformly random empty child slot, so the expected
height is logarithmic) and n distinct values from the full 32-bit range are placed by an
in-order walk, which makes a valid binary search tree. Three times in ten the smallest and
largest values are the 32-bit extremes. Then:

- 50%: the tree stays valid;
- 15% (at least 2 nodes): two values trade places, which always breaks the order;
- 15% (at least 2 nodes): one value is overwritten by its in-order neighbour, a duplicate;
- 20%: a node keeps the right side of its parent but crosses a bound set by a higher
  ancestor, the trap that a parent-only check misses (falls back to a swap when no node
  has such a bound).
"""

import random
from collections import deque

MAX_NODES = 10**5
MAX_HEIGHT = 3000
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
EXTREMES_PROBABILITY = 0.3
NO_CHILD = -1


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES)
    left, right = _random_shape(rng, size)
    order = _in_order(left, right)
    sorted_values = sorted(rng.sample(range(INT_MIN, INT_MAX + 1), size))
    if rng.random() < EXTREMES_PROBABILITY:
        sorted_values[0] = INT_MIN
        sorted_values[-1] = INT_MAX
    values = [0] * size
    for rank, node in enumerate(order):
        values[node] = sorted_values[rank]
    roll = rng.random()
    if roll < 0.5:
        pass
    elif roll < 0.65 and size >= 2:
        first, second = rng.sample(range(size), 2)
        values[first], values[second] = values[second], values[first]
    elif roll < 0.80 and size >= 2:
        rank = rng.randrange(size - 1)
        values[order[rank]] = values[order[rank + 1]]
    elif roll >= 0.80:
        _cross_ancestor_bound(rng, left, right, values)
    return {"root": _level_order(left, right, values)}


def validate(case_input: dict) -> None:
    root = case_input["root"]
    nodes = [value for value in root if value is not None]
    assert len(nodes) <= MAX_NODES, "too many nodes"
    assert all(INT_MIN <= value <= INT_MAX for value in nodes), "value out of range"
    assert not root or root[0] is not None, "a non-empty tree needs a root value"
    assert not root or root[-1] is not None, "trailing nulls must be trimmed"
    assert _height(root) <= MAX_HEIGHT, "tree too tall"


def _cross_ancestor_bound(rng: random.Random, left: list[int], right: list[int], values: list[int]) -> None:
    """Move one node's value past an ancestor's bound while it still fits next to its parent."""
    candidates: list[tuple[int, int, int]] = []  # (node, new low end, new high end)
    pending: list[tuple[int, int | None, int | None, int]] = [(0, None, None, 0)]
    while pending:
        node, low, high, side = pending.pop()
        if side < 0 and low is not None:
            candidates.append((node, max(INT_MIN, low - 1000), low))
        if side > 0 and high is not None:
            candidates.append((node, high, min(INT_MAX, high + 1000)))
        if left[node] != NO_CHILD:
            pending.append((left[node], low, values[node], -1))
        if right[node] != NO_CHILD:
            pending.append((right[node], values[node], high, 1))
    if not candidates:
        if len(values) > 1:
            other = rng.randrange(1, len(values))
            values[0], values[other] = values[other], values[0]
        return
    node, low_end, high_end = rng.choice(candidates)
    values[node] = rng.randint(low_end, high_end)


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
    if not root:
        return 0
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
