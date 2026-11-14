from cs_support import TreeNode


def level_order(root: TreeNode | None) -> list[list[int]]:
    levels: list[list[int]] = []
    # Pre-order with an explicit stack; pushing right before left visits left first.
    pending = [(root, 0)] if root is not None else []
    while pending:
        node, depth = pending.pop()
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node.val)
        if node.right is not None:
            pending.append((node.right, depth + 1))
        if node.left is not None:
            pending.append((node.left, depth + 1))
    return levels
