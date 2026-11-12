"""The four classic orders for visiting a binary tree, each written twice: recursively, and with
an explicit stack or queue. Both versions must agree."""

from collections import deque
from dataclasses import dataclass


@dataclass
class Node:
    label: str
    left: "Node | None" = None
    right: "Node | None" = None


# The tree drawn in the guide:
#          A
#        /   \
#       B     C
#      / \   / \
#     D   E F   G
#        /
#       H
tree = Node(
    "A",
    Node("B", Node("D"), Node("E", Node("H"))),
    Node("C", Node("F"), Node("G")),
)


def preorder(node: Node | None, out: list[str]) -> list[str]:
    if node:
        out.append(node.label)  # the node first,
        preorder(node.left, out)  # then its whole left subtree,
        preorder(node.right, out)  # then its whole right subtree
    return out


def inorder(node: Node | None, out: list[str]) -> list[str]:
    if node:
        inorder(node.left, out)
        out.append(node.label)  # the node between its two subtrees
        inorder(node.right, out)
    return out


def postorder(node: Node | None, out: list[str]) -> list[str]:
    if node:
        postorder(node.left, out)
        postorder(node.right, out)
        out.append(node.label)  # the node after both subtrees
    return out


def with_stack(root: Node | None, order: str) -> list[str]:
    """Any of the three depth-first orders, with a stack of (node, ready) pairs.

    A pair that is not ready stands for "this whole subtree, still to do"; a ready pair stands
    for "visit this node now". Expanding a subtree pushes its plan in reverse, because a stack
    hands back the last thing pushed first."""
    out: list[str] = []
    stack: list[tuple[Node | None, bool]] = [(root, False)]
    while stack:
        node, ready = stack.pop()
        if node is None:
            continue
        if ready:
            out.append(node.label)
            continue
        visit, left, right = (node, True), (node.left, False), (node.right, False)
        plan = {
            "pre": [visit, left, right],
            "in": [left, visit, right],
            "post": [left, right, visit],
        }[order]
        stack.extend(reversed(plan))
    return out


def level_order(root: Node | None) -> list[str]:
    """Breadth first: a queue hands nodes back in the order they were added."""
    out: list[str] = []
    queue: deque[Node | None] = deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            continue
        out.append(node.label)
        queue.append(node.left)
        queue.append(node.right)
    return out


for name, recursive in (("pre", preorder), ("in", inorder), ("post", postorder)):
    walked = recursive(tree, [])
    same = walked == with_stack(tree, name)
    print(f"{name + '-order:':<12} {' '.join(walked)}   (stack version agrees: {same})")
print(f"{'level order:':<12} {' '.join(level_order(tree))}")
