from cs_support import TreeNode


def max_path_sum(root: TreeNode | None) -> int:
    turning_here = root.val + max(0, _gain(root.left)) + max(0, _gain(root.right))
    best = turning_here
    for child in (root.left, root.right):
        if child is not None:
            best = max(best, max_path_sum(child))
    return best


def _gain(node: TreeNode | None) -> int:
    """Largest sum of a path that starts at `node` and only goes down (0 for no node)."""
    if node is None:
        return 0
    return node.val + max(0, _gain(node.left), _gain(node.right))
