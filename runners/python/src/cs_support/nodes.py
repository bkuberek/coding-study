from __future__ import annotations

REPR_LIST_LIMIT = 10
"""How many values `repr(list_node)` shows before eliding the rest."""


class ListNode:
    """A singly linked list node."""

    def __init__(self, val: int = 0, next: ListNode | None = None) -> None:
        self.val = val
        self.next = next

    def __repr__(self) -> str:
        values: list[str] = []
        seen: set[int] = set()
        node: ListNode | None = self
        while node is not None and len(values) < REPR_LIST_LIMIT:
            if id(node) in seen:
                return f"ListNode({' -> '.join(values)} -> (cycle))"
            seen.add(id(node))
            values.append(repr(node.val))
            node = node.next
        suffix = " -> ..." if node is not None else ""
        return f"ListNode({' -> '.join(values)}{suffix})"


class TreeNode:
    """A binary tree node."""

    def __init__(
        self, val: int = 0, left: TreeNode | None = None, right: TreeNode | None = None
    ) -> None:
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"TreeNode({self.val!r})"


class GraphNode:
    """An undirected graph node; `neighbors` holds the adjacent nodes."""

    def __init__(self, val: int = 0, neighbors: list[GraphNode] | None = None) -> None:
        self.val = val
        self.neighbors: list[GraphNode] = neighbors if neighbors is not None else []

    def __repr__(self) -> str:
        adjacent = ", ".join(repr(neighbor.val) for neighbor in self.neighbors)
        return f"GraphNode({self.val!r}, neighbors=[{adjacent}])"
