"""Seeded inputs for same-tree: a random tree and a second tree that is often almost equal.

`p` has a random shape (each node fills a uniformly random empty child slot, so the expected
height is logarithmic). `q` is chosen so that both answers are common:

- 40%: an exact copy of `p` (the answer is true and every node is compared);
- 15%: the copy with one value changed;
- 15%: the copy with one extra leaf, randomly swapped with `p` so either tree can be bigger;
- 15%: the copy with the two children of one node swapped (a local mirror);
- 15%: an independent random tree of the same size.

Half of the inputs draw values from [-3, 3], so equal values in different shapes are common.
"""

import random
from collections import deque

MAX_NODES = 10**5
MAX_HEIGHT = 3000
VALUE_LIMIT = 10**4
SMALL_LIMIT = 3
NO_CHILD = -1


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES - 1)
    limit = SMALL_LIMIT if rng.random() < 0.5 else VALUE_LIMIT
    left, right = _random_shape(rng, size)
    values = [rng.randint(-limit, limit) for _ in range(size)]
    p = _level_order(left, right, values)
    roll = rng.random()
    if roll < 0.40:
        q = list(p)
    elif roll < 0.55:
        changed = list(values)
        node = rng.randrange(size)
        changed[node] = _other_value(rng, values[node], limit)
        q = _level_order(left, right, changed)
    elif roll < 0.70:
        q = _with_extra_leaf(rng, left, right, values, limit)
        if rng.random() < 0.5:
            p, q = q, p
    elif roll < 0.85:
        node = rng.randrange(size)
        mirrored_left, mirrored_right = list(left), list(right)
        mirrored_left[node], mirrored_right[node] = right[node], left[node]
        q = _level_order(mirrored_left, mirrored_right, values)
    else:
        other_left, other_right = _random_shape(rng, size)
        q = _level_order(other_left, other_right, [rng.randint(-limit, limit) for _ in range(size)])
    return {"p": p, "q": q}


def validate(case_input: dict) -> None:
    for name in ("p", "q"):
        root = case_input[name]
        nodes = [value for value in root if value is not None]
        assert len(nodes) <= MAX_NODES, f"{name}: too many nodes"
        assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nodes), f"{name}: value out of range"
        assert not root or root[0] is not None, f"{name}: a non-empty tree needs a root value"
        assert not root or root[-1] is not None, f"{name}: trailing nulls must be trimmed"
        assert _height(root) <= MAX_HEIGHT, f"{name}: tree too tall"


def _other_value(rng: random.Random, value: int, limit: int) -> int:
    replacement = rng.randint(-limit, limit - 1)
    return replacement + 1 if replacement >= value else replacement


def _with_extra_leaf(
    rng: random.Random, left: list[int], right: list[int], values: list[int], limit: int
) -> list[int | None]:
    empty_slots = [(node, side) for node in range(len(values)) for side in (0, 1) if (left, right)[side][node] == NO_CHILD]
    parent, side = rng.choice(empty_slots)
    grown_left, grown_right = left + [NO_CHILD], right + [NO_CHILD]
    (grown_left, grown_right)[side][parent] = len(values)
    return _level_order(grown_left, grown_right, values + [rng.randint(-limit, limit)])


def _random_shape(rng: random.Random, size: int) -> tuple[list[int], list[int]]:
    left = [NO_CHILD] * size
    right = [NO_CHILD] * size
    empty_slots = [(0, left), (0, right)] if size else []
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
    queue = deque([0] if values else [])
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
