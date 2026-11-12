"""What a walk keeps in memory. Recursion and an explicit stack grow with the height of the
tree; a queue grows with its widest level."""

import sys
from collections import deque


class Node:
    __slots__ = ("left", "right")

    def __init__(self, left: "Node | None" = None, right: "Node | None" = None) -> None:
        self.left, self.right = left, right


def path(n: int) -> Node | None:
    """A degenerate tree: n nodes, each the left child of the one above."""
    root = None
    for _ in range(n):
        root = Node(left=root)
    return root


def perfect(height: int) -> Node | None:
    """A perfect tree: every level full, 2 ** (height + 1) - 1 nodes."""
    if height < 0:
        return None
    return Node(perfect(height - 1), perfect(height - 1))


def visit_recursively(node: Node | None, seen: list[Node]) -> None:
    if node:
        visit_recursively(node.left, seen)
        seen.append(node)
        visit_recursively(node.right, seen)


def visit_with_stack(root: Node | None) -> tuple[int, int]:
    """In-order with a stack of (node, ready) pairs; returns (nodes visited, largest stack)."""
    visited, peak = 0, 0
    stack: list[tuple[Node | None, bool]] = [(root, False)]
    while stack:
        peak = max(peak, len(stack))
        node, ready = stack.pop()
        if node is None:
            continue
        if ready:
            visited += 1
        else:
            stack.extend([(node.right, False), (node, True), (node.left, False)])
    return visited, peak


def visit_with_queue(root: Node | None) -> tuple[int, int]:
    """Level order; returns (nodes visited, largest queue)."""
    visited, peak = 0, 0
    queue = deque([root] if root else [])
    while queue:
        peak = max(peak, len(queue))
        node = queue.popleft()
        visited += 1
        queue.extend(child for child in (node.left, node.right) if child)
    return visited, peak


deep = path(100_000)
print("recursion limit:", sys.getrecursionlimit())
try:
    visit_recursively(deep, [])
except RecursionError:
    print("path of 100,000 nodes, recursive walk: RecursionError")
visited, peak = visit_with_stack(deep)
print(f"path of 100,000 nodes, stack walk: visited {visited}, stack peaked at {peak}")

bushy = perfect(16)
visited, peak = visit_with_stack(bushy)
print(f"perfect tree of height 16, stack walk: visited {visited}, stack peaked at {peak}")
visited, peak = visit_with_queue(bushy)
print(f"perfect tree of height 16, queue walk: visited {visited}, queue peaked at {peak}")
