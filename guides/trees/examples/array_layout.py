"""A complete binary tree stored in a plain list, with no links at all.

The list holds the nodes level by level, left to right. Index arithmetic finds a node's parent
and children, and the depth of index i is floor(log2(i + 1))."""

tree = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]


def parent(i: int) -> int | None:
    return (i - 1) // 2 if i > 0 else None


def children(i: int) -> list[int]:
    return [c for c in (2 * i + 1, 2 * i + 2) if c < len(tree)]


for i, label in enumerate(tree):
    up = "-" if parent(i) is None else tree[parent(i)]
    down = " ".join(tree[c] for c in children(i)) or "none, a leaf"
    depth = (i + 1).bit_length() - 1
    print(f"index {i}: {label}, depth {depth}, parent {up}, children {down}")
