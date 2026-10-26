"""Linked structures and their JSON encodings (docs/specs/problem-format.md, "Serialization of
linked structures").

Inputs are built from `cs_support` classes. Outputs are read by duck typing (`val`, `next`,
`left`, `right`, `neighbors`), never with isinstance, so any class with those fields works.
"""

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from itertools import pairwise
from typing import cast

from cs_runner.dsl import NodeKind
from cs_runner.errors import CaseInputError, InvalidOutputError
from cs_runner.json_value import Json, is_int, type_name
from cs_support import GraphNode, ListNode, TreeNode

MAX_LIST_NODES = 100_000
"""Output lists stop here: longer lists are reported as too long or cyclic."""
CYCLIC_VALUES = "values"
CYCLE_AT = "cycle_at"
_SUCCESSOR_FIELDS: Mapping[NodeKind, tuple[str, ...]] = {
    NodeKind.LIST_NODE: ("next",),
    NodeKind.TREE_NODE: ("left", "right"),
}
_MISSING = object()


def build_list(encoded: Json) -> ListNode | None:
    """`[1, 2, 3]`, or `{"values": [...], "cycle_at": k}` whose tail links back to node `k`."""
    values, cycle_at = _list_encoding(encoded)
    nodes = [ListNode(_input_value(value)) for value in values]
    for node, successor in pairwise(nodes):
        node.next = successor
    if cycle_at is not None:
        nodes[-1].next = nodes[cycle_at]
    return nodes[0] if nodes else None


def build_tree(encoded: Json) -> TreeNode | None:
    """Level order with `null` for missing children."""
    values = _input_array(encoded, NodeKind.TREE_NODE)
    if not values or values[0] is None:
        return None
    root = TreeNode(_input_value(values[0]))
    children = iter(values[1:])
    parents = deque([root])
    while parents:
        parent = parents.popleft()
        parent.left = _tree_child(next(children, None))
        parent.right = _tree_child(next(children, None))
        parents.extend(child for child in (parent.left, parent.right) if child is not None)
    return root


def build_graph(encoded: Json) -> GraphNode | None:
    """A 1-indexed adjacency list where node `i` has value `i`; returns node 1."""
    adjacency = _input_array(encoded, NodeKind.GRAPH_NODE)
    nodes = [GraphNode(value) for value in range(1, len(adjacency) + 1)]
    for node, neighbors in zip(nodes, adjacency, strict=True):
        values = _input_array(neighbors, f"the neighbors of graph node {node.val}")
        node.neighbors = [nodes[_neighbor_index(value, len(nodes))] for value in values]
    return nodes[0] if nodes else None


def encode_list(head: object) -> list[Json]:
    values: list[Json] = []
    node = head
    while node is not None:
        if len(values) == MAX_LIST_NODES:
            raise InvalidOutputError("list too long or cyclic")
        values.append(node_value(node))
        node = _field(node, "next")
    return values


def encode_tree(root: object) -> list[Json]:
    values: list[Json] = []
    seen: set[int] = set()
    pending: deque[object] = deque([root])
    while pending:
        node = pending.popleft()
        if node is None:
            values.append(None)
            continue
        if id(node) in seen:
            raise InvalidOutputError("tree contains a cycle or a shared node")
        seen.add(id(node))
        values.append(node_value(node))
        pending.extend((_field(node, "left"), _field(node, "right")))
    while values and values[-1] is None:
        values.pop()
    return values


def encode_graph(start: object) -> list[Json]:
    """Neighbor values of nodes 1..k, where k nodes are reachable from `start`."""
    if start is None:
        return []
    by_value: dict[int, object] = {}
    for node in _reachable_graph_nodes(start):
        value = node_value(node)
        if value in by_value:
            raise InvalidOutputError(f"graph has two nodes with value {value}")
        by_value[value] = node
    if set(by_value) != set(range(1, len(by_value) + 1)):
        raise InvalidOutputError("graph node values must be exactly 1..k for k reachable nodes")
    return [_neighbor_values(by_value[value]) for value in range(1, len(by_value) + 1)]


def node_value(node: object) -> int:
    value = _field(node, "val")
    if not is_int(value):
        raise InvalidOutputError(f"node value must be an int, got {type_name(value)}")
    return value


def traverse(root: object, kind: NodeKind) -> list[object]:
    """Every node reachable from `root`, each once, in traversal order: list order, level order
    for trees, breadth-first for graphs. Cycles are allowed."""
    order: list[object] = []
    seen: set[int] = set()
    pending: deque[object] = deque([root])
    while pending:
        node = pending.popleft()
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        order.append(node)
        pending.extend(_successors(node, kind))
    return order


NODE_BUILDERS: Mapping[NodeKind, Callable[[Json], object]] = {
    NodeKind.LIST_NODE: build_list,
    NodeKind.TREE_NODE: build_tree,
    NodeKind.GRAPH_NODE: build_graph,
}
NODE_ENCODERS: Mapping[NodeKind, Callable[[object], list[Json]]] = {
    NodeKind.LIST_NODE: encode_list,
    NodeKind.TREE_NODE: encode_tree,
    NodeKind.GRAPH_NODE: encode_graph,
}


def _list_encoding(encoded: Json) -> tuple[list[Json], int | None]:
    if isinstance(encoded, list):
        return encoded, None
    if isinstance(encoded, dict):
        values, cycle_at = encoded.get(CYCLIC_VALUES), encoded.get(CYCLE_AT)
        if isinstance(values, list) and is_int(cycle_at) and 0 <= cycle_at < len(values):
            return values, cycle_at
    raise CaseInputError(f"not a {NodeKind.LIST_NODE} encoding: {encoded!r}")


def _input_array(encoded: Json, description: str) -> list[Json]:
    if not isinstance(encoded, list):
        raise CaseInputError(f"expected an array for {description}, got {encoded!r}")
    return encoded


def _input_value(value: Json) -> int:
    if not is_int(value):
        raise CaseInputError(f"node value must be an int, got {value!r}")
    return value


def _tree_child(value: Json) -> TreeNode | None:
    return None if value is None else TreeNode(_input_value(value))


def _neighbor_index(value: Json, node_count: int) -> int:
    if not is_int(value) or not 1 <= value <= node_count:
        raise CaseInputError(f"graph neighbor {value!r} is not a node value 1..{node_count}")
    return value - 1


def _field(node: object, name: str) -> object:
    value = getattr(node, name, _MISSING)
    if value is _MISSING:
        raise InvalidOutputError(f"{type_name(node)} object has no field .{name}")
    return value


def _neighbors(node: object) -> Sequence[object]:
    neighbors = _field(node, "neighbors")
    if not isinstance(neighbors, list | tuple):
        raise InvalidOutputError(f"neighbors must be a list, got {type_name(neighbors)}")
    items = cast("Sequence[object]", neighbors)
    if any(neighbor is None for neighbor in items):
        raise InvalidOutputError("neighbors must not contain null")
    return items


def _neighbor_values(node: object) -> list[Json]:
    return [node_value(neighbor) for neighbor in _neighbors(node)]


def _reachable_graph_nodes(start: object) -> list[object]:
    order = [start]
    seen = {id(start)}
    pending: deque[object] = deque([start])
    while pending:
        for neighbor in _neighbors(pending.popleft()):
            if id(neighbor) not in seen:
                seen.add(id(neighbor))
                order.append(neighbor)
                pending.append(neighbor)
    return order


def _successors(node: object, kind: NodeKind) -> list[object]:
    if kind is NodeKind.GRAPH_NODE:
        neighbors = getattr(node, "neighbors", ())
        return (
            list(cast("Sequence[object]", neighbors)) if isinstance(neighbors, list | tuple) else []
        )
    return [getattr(node, name, None) for name in _SUCCESSOR_FIELDS[kind]]
