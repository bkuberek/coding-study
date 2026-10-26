from cs_support import TreeNode


def is_valid_bst(root: TreeNode | None) -> bool:
    return _within(root, None, None)


def _within(node: TreeNode | None, low: int | None, high: int | None) -> bool:
    """Is every value of the subtree strictly between `low` and `high` (None: unbounded)?"""
    if node is None:
        return True
    if (low is not None and node.val <= low) or (high is not None and node.val >= high):
        return False
    return _within(node.left, low, node.val) and _within(node.right, node.val, high)
