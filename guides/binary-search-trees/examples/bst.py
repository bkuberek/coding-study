"""A binary search tree of distinct integer keys: search, insert, the nearest key at or below a
value, delete, and the in-order listing."""

from dataclasses import dataclass


@dataclass
class Node:
    key: int
    left: "Node | None" = None
    right: "Node | None" = None


def search(root: Node | None, key: int) -> list[int]:
    """The keys compared on the way down; the last one is the key itself if it is present."""
    path = []
    node = root
    while node:
        path.append(node.key)
        if key == node.key:
            break
        node = node.left if key < node.key else node.right
    return path


def insert(root: Node | None, key: int) -> Node:
    if root is None:
        return Node(key)
    if key < root.key:
        root.left = insert(root.left, key)
    elif key > root.key:
        root.right = insert(root.right, key)
    return root  # an equal key is already present: nothing changes


def floor(root: Node | None, value: int) -> int | None:
    """The largest key that is at most value, or None."""
    best = None
    node = root
    while node:
        if node.key <= value:
            best = node.key  # a candidate; a larger one can only be to the right
            node = node.right
        else:
            node = node.left
    return best


def delete(root: Node | None, key: int) -> Node | None:
    if root is None:
        return None
    if key < root.key:
        root.left = delete(root.left, key)
    elif key > root.key:
        root.right = delete(root.right, key)
    elif root.left is None:  # no child, or only a right child: lift it up
        return root.right
    elif root.right is None:  # only a left child
        return root.left
    else:  # two children: take the smallest key of the right subtree
        successor = root.right
        while successor.left:
            successor = successor.left
        root.key = successor.key
        root.right = delete(root.right, successor.key)
    return root


def in_order(node: Node | None) -> list[int]:
    if node is None:
        return []
    return [*in_order(node.left), node.key, *in_order(node.right)]


root = None
for key in [41, 20, 65, 11, 29, 50, 91, 32, 72, 99]:
    root = insert(root, key)
print("in-order:", in_order(root))
print("search 32 compares", search(root, 32))
print("search 55 compares", search(root, 55), "and falls off: not found")
print("floor(55) =", floor(root, 55), "| floor(10) =", floor(root, 10))

for key in (65, 29, 11):  # two children, then one child, then none
    root = delete(root, key)
    print(f"delete {key}: in-order {in_order(root)}")
print("the root's children are now", root.left.key, "and", root.right.key)
