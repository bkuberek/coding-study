"""Seeded inputs for tree-path-sum-count: deep trees, so walking down from every node is quadratic.

`n` is the number of nodes. Each new node either extends the current deepest node (with
probability 1/2, while the height stays under the cap) or fills a uniformly random free
child slot. The height is therefore about n / 2, and the brute force walks O(n * h) =
O(n^2) steps; the cap keeps recursion within the runners' limits. Node values come from a
range picked per input, from {-1, 0, 1} up to the full range, so small ranges produce many
matching paths. `targetSum` is the sum of a random downward path (at least one answer) or,
one time in five, a random value.
"""

import random
from collections import deque

MAX_NODES = 3000
MAX_HEIGHT = 2000
VALUE_LIMIT = 1000
TARGET_LIMIT = 10**6
VALUE_RANGES = [1, 3, 10, VALUE_LIMIT]
SPINE_SHARE = 0.5
RANDOM_TARGET_SHARE = 0.2


def _shape(rng: random.Random, size: int) -> tuple[list[int], list[int], list[int]]:
    left, right, depth = [-1] * size, [-1] * size, [0] * size
    free = [(0, 0), (0, 1)]  # (parent, side) slots that can take a child
    deepest = 0
    for node in range(1, size):
        if rng.random() < SPINE_SHARE and depth[deepest] + 1 < MAX_HEIGHT:
            parent, side = deepest, rng.randrange(2)
            if (left, right)[side][parent] != -1:
                side = 1 - side
        else:
            index = rng.randrange(len(free))
            while (left, right)[free[index][1]][free[index][0]] != -1:
                free[index] = free[-1]
                free.pop()
                index = rng.randrange(len(free))
            parent, side = free[index]
        (left, right)[side][parent] = node
        depth[node] = depth[parent] + 1
        free.extend([(node, 0), (node, 1)])
        if depth[node] > depth[deepest]:
            deepest = node
    return left, right, depth


def _level_order(values: list[int], left: list[int], right: list[int]) -> list[int | None]:
    encoded: list[int | None] = [values[0]]
    queue = deque([0])
    while queue:
        node = queue.popleft()
        for child in (left[node], right[node]):
            encoded.append(None if child == -1 else values[child])
            if child != -1:
                queue.append(child)
    while encoded[-1] is None:
        encoded.pop()
    return encoded


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES)
    left, right, depth = _shape(rng, size)
    limit = rng.choice(VALUE_RANGES)
    values = [rng.randint(-limit, limit) for _ in range(size)]
    if rng.random() < RANDOM_TARGET_SHARE:
        target = rng.randint(-4 * limit, 4 * limit)
    else:
        # Sum the path from a random node down a random number of steps.
        node, target = rng.randrange(size), 0
        while True:
            target += values[node]
            children = [c for c in (left[node], right[node]) if c != -1]
            if not children or rng.random() < 0.2:
                break
            node = rng.choice(children)
    target = max(-TARGET_LIMIT, min(TARGET_LIMIT, target))
    return {"root": _level_order(values, left, right), "targetSum": target}


def validate(case_input: dict) -> None:
    root, target = case_input["root"], case_input["targetSum"]
    values = [value for value in root if value is not None]
    assert len(values) <= MAX_NODES, "too many nodes"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in values), "value out of range"
    assert -TARGET_LIMIT <= target <= TARGET_LIMIT, "targetSum out of range"
