"""Seeded operation sequences for bst-iterator.

`n` is the number of nodes. The shape is random (each node fills a uniformly random empty
child slot, so the expected height is logarithmic) and n distinct values from [0, 10^6] are
placed by an in-order walk, which makes a valid binary search tree. Before each `next` there is
a `hasNext` with probability 1/2. Four times in five the sequence returns every value and ends
with one or two `hasNext` calls that see the end; otherwise it stops after a random number of
values. Total calls stay at most about 2n + 2.
"""

import random
from collections import deque

MAX_NODES = 10**5
MAX_HEIGHT = 3000
VALUE_LIMIT = 10**6
NO_CHILD = -1


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES)
    left, right = _random_shape(rng, size)
    sorted_values = sorted(rng.sample(range(VALUE_LIMIT + 1), size))
    values = [0] * size
    for rank, node in enumerate(_in_order(left, right)):
        values[node] = sorted_values[rank]
    ops: list[str] = ["BSTIterator"]
    args: list[list] = [[_level_order(left, right, values)]]
    exhaust = rng.random() < 0.8
    calls_to_next = size if exhaust else rng.randint(0, size)
    for _ in range(calls_to_next):
        if rng.random() < 0.5:
            ops.append("hasNext")
            args.append([])
        ops.append("next")
        args.append([])
    if exhaust:
        for _ in range(rng.randint(1, 2)):
            ops.append("hasNext")
            args.append([])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "BSTIterator" and len(args[0]) == 1, "the first op must be the constructor"
    root = args[0][0]
    nodes = [value for value in root if value is not None]
    assert len(nodes) <= MAX_NODES, "too many nodes"
    assert all(0 <= value <= VALUE_LIMIT for value in nodes), "value out of range"
    assert len(set(nodes)) == len(nodes), "values must be distinct"
    assert not root or (root[0] is not None and root[-1] is not None), "bad level-order encoding"
    assert _height(root) <= MAX_HEIGHT, "tree too tall"
    assert len(ops) - 1 <= 2 * 10**5, "too many calls"
    remaining = len(nodes)
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op in ("next", "hasNext") and arguments == [], f"bad call {op}{arguments}"
        if op == "next":
            assert remaining > 0, "next called after the last value"
            remaining -= 1


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
