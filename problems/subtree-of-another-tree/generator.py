"""Seeded inputs for subtree-of-another-tree.

`root` has a random shape (each node fills a uniformly random empty child slot, so the expected
height is logarithmic).

Below 100 nodes, which covers the oracle's inputs, `subRoot` is chosen so that both answers
are common:

- 50%: a copy of the subtree under some node of `root` (true);
- 25%: such a copy with one value changed or one extra leaf (usually false);
- 25%: an independent random tree with up to a tenth as many nodes (usually false).

The copied node is uniform half the time and otherwise reached by walking 0 to 3 random steps
down from the root, so large subtrees occur too. Half of these inputs draw values from [-3, 3],
so partial matches with equal values are frequent.

From 100 nodes on, the sizes the ladder times, every input draws values from [-3, 3] and
`subRoot` is the whole of `root` with the value of its last node in pre-order changed, so the
answer is false. Checking the root then compares every node before the difference shows up,
and every other node is checked too, at every seed. A true answer would let both approaches
stop at a match whose position changes from seed to seed.
"""

import random
from collections import deque

MAX_NODES = 10**5
MAX_HEIGHT = 3000
VALUE_LIMIT = 10**4
SMALL_LIMIT = 3
NO_CHILD = -1
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), MAX_NODES - 1)
    uniform = size >= UNIFORM_FROM
    limit = SMALL_LIMIT if uniform or rng.random() < 0.5 else VALUE_LIMIT
    left, right = _random_shape(rng, size)
    values = [rng.randint(-limit, limit) for _ in range(size)]
    root = _level_order(left, right, values, 0)
    if uniform:
        changed = list(values)
        last = _last_in_preorder(left, right)
        changed[last] = _other_value(rng, values[last], limit)
        return {"root": root, "subRoot": _level_order(left, right, changed, 0)}
    roll = rng.random()
    if roll < 0.75:
        top = _pick_node(rng, left, right)
        if roll < 0.5:
            sub_root = _level_order(left, right, values, top)
        else:
            sub_root = _mutated_copy(rng, left, right, values, top, limit)
    else:
        sub_size = rng.randint(1, max(1, size // 10))
        sub_left, sub_right = _random_shape(rng, sub_size)
        sub_values = [rng.randint(-limit, limit) for _ in range(sub_size)]
        sub_root = _level_order(sub_left, sub_right, sub_values, 0)
    return {"root": root, "subRoot": sub_root}


def validate(case_input: dict) -> None:
    for name in ("root", "subRoot"):
        tree = case_input[name]
        nodes = [value for value in tree if value is not None]
        assert 1 <= len(nodes) <= MAX_NODES, f"{name}: node count out of range"
        assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nodes), f"{name}: value out of range"
        assert tree[0] is not None, f"{name}: a non-empty tree needs a root value"
        assert tree[-1] is not None, f"{name}: trailing nulls must be trimmed"
        assert _height(tree) <= MAX_HEIGHT, f"{name}: tree too tall"


def _pick_node(rng: random.Random, left: list[int], right: list[int]) -> int:
    if rng.random() < 0.5:
        return rng.randrange(len(left))
    node = 0
    for _ in range(rng.randint(0, 3)):
        children = [child for child in (left[node], right[node]) if child != NO_CHILD]
        if not children:
            break
        node = rng.choice(children)
    return node


def _mutated_copy(
    rng: random.Random, left: list[int], right: list[int], values: list[int], top: int, limit: int
) -> list[int | None]:
    members = _subtree_nodes(left, right, top)
    if rng.random() < 0.5:
        changed = list(values)
        node = rng.choice(members)
        changed[node] = _other_value(rng, values[node], limit)
        return _level_order(left, right, changed, top)
    empty_slots = [(node, side) for node in members for side in (0, 1) if (left, right)[side][node] == NO_CHILD]
    parent, side = rng.choice(empty_slots)
    grown_left, grown_right = left + [NO_CHILD], right + [NO_CHILD]
    (grown_left, grown_right)[side][parent] = len(values)
    return _level_order(grown_left, grown_right, values + [rng.randint(-limit, limit)], top)


def _other_value(rng: random.Random, value: int, limit: int) -> int:
    """A value in [-limit, limit] other than `value`."""
    replacement = rng.randint(-limit, limit - 1)
    return replacement + 1 if replacement >= value else replacement


def _last_in_preorder(left: list[int], right: list[int]) -> int:
    """The node a pre-order walk from node 0 visits last."""
    last = 0
    pending = [0]
    while pending:
        last = pending.pop()
        pending.extend(child for child in (right[last], left[last]) if child != NO_CHILD)
    return last


def _subtree_nodes(left: list[int], right: list[int], top: int) -> list[int]:
    members = [top]
    for node in members:
        members.extend(child for child in (left[node], right[node]) if child != NO_CHILD)
    return members


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
