from cs_support import TreeNode

UNBALANCED = -1


def is_balanced(root: TreeNode | None) -> bool:
    return _checked_height(root) != UNBALANCED


def _checked_height(node: TreeNode | None) -> int:
    """Height of `node`, or UNBALANCED as soon as any subtree below it is unbalanced."""
    if node is None:
        return 0
    left = _checked_height(node.left)
    if left == UNBALANCED:
        return UNBALANCED
    right = _checked_height(node.right)
    if right == UNBALANCED or abs(left - right) > 1:
        return UNBALANCED
    return 1 + max(left, right)
