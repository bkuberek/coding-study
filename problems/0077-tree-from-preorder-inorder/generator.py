"""Seeded inputs for tree-from-preorder-inorder.

The shape is random (each node fills a uniformly random empty child slot, so the expected
height is logarithmic) and the values are n distinct integers from [-10^9, 10^9] in random
positions, so the tree is not a search tree. The input is the tree's pre-order and in-order
walks.
"""

import random

MAX_NODES = 10**5
MAX_HEIGHT = 3000
VALUE_LIMIT = 10**9
NO_CHILD = -1


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES)
    left, right = _random_shape(rng, size)
    values = rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), size)
    return {
        "preorder": [values[node] for node in _pre_order(left, right)],
        "inorder": [values[node] for node in _in_order(left, right)],
    }


def validate(case_input: dict) -> None:
    preorder, inorder = case_input["preorder"], case_input["inorder"]
    assert len(preorder) == len(inorder) <= MAX_NODES, "lengths differ or are too large"
    assert len(set(preorder)) == len(preorder), "values must be distinct"
    assert set(preorder) == set(inorder), "the walks must hold the same values"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in preorder), "value out of range"
    assert _height(preorder, inorder) <= MAX_HEIGHT, "tree too tall"


def _height(preorder: list[int], inorder: list[int]) -> int:
    """Height of the tree the walks describe; raises AssertionError if they are inconsistent."""
    position = {value: index for index, value in enumerate(inorder)}
    height = 0
    cursor = 0
    pending = [(0, len(inorder), 1)] if inorder else []
    while pending:
        low, high, depth = pending.pop()
        assert cursor < len(preorder), "walks are inconsistent"
        split = position[preorder[cursor]]
        assert low <= split < high, "walks are inconsistent"
        cursor += 1
        height = max(height, depth)
        # Pre-order handles the left part first, so it is pushed last.
        if split + 1 < high:
            pending.append((split + 1, high, depth + 1))
        if low < split:
            pending.append((low, split, depth + 1))
    return height


def _pre_order(left: list[int], right: list[int]) -> list[int]:
    order: list[int] = []
    pending = [0]
    while pending:
        node = pending.pop()
        order.append(node)
        if right[node] != NO_CHILD:
            pending.append(right[node])
        if left[node] != NO_CHILD:
            pending.append(left[node])
    return order


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
