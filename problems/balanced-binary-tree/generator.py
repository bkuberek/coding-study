"""Seeded inputs for balanced-binary-tree: AVL trees, nearly-AVL trees and random shapes.

Below 100 nodes, which covers the oracle's inputs, each input takes one of three shapes:

- 45%: the shape of an AVL tree built by inserting a random permutation, so the tree is
  height-balanced and its height is about 1.44 log n;
- 30% (at least 3 nodes): an AVL tree of n - 2 nodes where one random leaf grows a two-node
  path to the left, which unbalances that leaf;
- 25%: a random shape where each node fills a uniformly random empty child slot, which is
  almost never balanced once the tree has more than a handful of nodes.

From 100 nodes on, the sizes the ladder times, every input is an AVL shape. A balanced tree is
the hard case for both approaches, because nothing short-circuits: the post-order check visits
every node and the top-down check computes heights under every node. An unbalanced tree would
let both stop at a node whose position changes from seed to seed.

Values are random and may repeat; balance never looks at them.
"""

import random
from collections import deque

MAX_NODES = 10**5
MAX_HEIGHT = 3000
VALUE_LIMIT = 10**4
NO_CHILD = -1
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES)
    roll = rng.random()
    if roll < 0.45 or (roll < 0.75 and size < 3) or size >= UNIFORM_FROM:
        top, left, right = _avl_shape(rng, size)
    elif roll < 0.75:
        top, left, right = _avl_shape(rng, size - 2)
        _grow_left_path(rng, left, right)
    else:
        top, left, right = 0, *_random_shape(rng, size)
    values = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(size)]
    return {"root": _level_order(left, right, values, top)}


def validate(case_input: dict) -> None:
    root = case_input["root"]
    nodes = [value for value in root if value is not None]
    assert len(nodes) <= MAX_NODES, "too many nodes"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nodes), "value out of range"
    assert not root or root[0] is not None, "a non-empty tree needs a root value"
    assert not root or root[-1] is not None, "trailing nulls must be trimmed"
    assert _height(root) <= MAX_HEIGHT, "tree too tall"


def _avl_shape(rng: random.Random, size: int) -> tuple[int, list[int], list[int]]:
    """Insert a random permutation of 0..size-1 into an AVL tree; return its root and links.

    Node ids are the keys themselves, so `key < node` compares keys and ids index the arrays.
    """
    keys = list(range(size))
    rng.shuffle(keys)
    left = [NO_CHILD] * size
    right = [NO_CHILD] * size
    heights = [1] * size

    def height(node: int) -> int:
        return heights[node] if node != NO_CHILD else 0

    def update(node: int) -> None:
        heights[node] = 1 + max(height(left[node]), height(right[node]))

    def rotate_right(node: int) -> int:
        pivot = left[node]
        left[node], right[pivot] = right[pivot], node
        update(node)
        update(pivot)
        return pivot

    def rotate_left(node: int) -> int:
        pivot = right[node]
        right[node], left[pivot] = left[pivot], node
        update(node)
        update(pivot)
        return pivot

    def rebalance(node: int) -> int:
        update(node)
        lean = height(left[node]) - height(right[node])
        if lean > 1:
            if height(left[left[node]]) < height(right[left[node]]):
                left[node] = rotate_left(left[node])
            return rotate_right(node)
        if lean < -1:
            if height(right[right[node]]) < height(left[right[node]]):
                right[node] = rotate_right(right[node])
            return rotate_left(node)
        return node

    def insert(node: int, key: int) -> int:
        if node == NO_CHILD:
            return key
        if key < node:
            left[node] = insert(left[node], key)
        else:
            right[node] = insert(right[node], key)
        return rebalance(node)

    top = NO_CHILD
    for key in keys:
        top = insert(top, key)
    return top, left, right


def _grow_left_path(rng: random.Random, left: list[int], right: list[int]) -> None:
    leaves = [node for node in range(len(left)) if left[node] == right[node] == NO_CHILD]
    leaf = rng.choice(leaves)
    child, grandchild = len(left), len(left) + 1
    left.extend([grandchild, NO_CHILD])
    right.extend([NO_CHILD, NO_CHILD])
    left[leaf] = child


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


def _level_order(left: list[int], right: list[int], values: list[int], top: int) -> list[int | None]:
    encoded: list[int | None] = []
    queue = deque([top])
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
