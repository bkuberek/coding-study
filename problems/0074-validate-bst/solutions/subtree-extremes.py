from cs_support import TreeNode


def is_valid_bst(root: TreeNode | None) -> bool:
    if root is None:
        return True
    if root.left is not None and _largest(root.left) >= root.val:
        return False
    if root.right is not None and _smallest(root.right) <= root.val:
        return False
    return is_valid_bst(root.left) and is_valid_bst(root.right)


def _largest(node: TreeNode) -> int:
    """Largest value anywhere in the subtree; it need not be a search tree, so scan it all."""
    best = node.val
    for child in (node.left, node.right):
        if child is not None:
            best = max(best, _largest(child))
    return best


def _smallest(node: TreeNode) -> int:
    best = node.val
    for child in (node.left, node.right):
        if child is not None:
            best = min(best, _smallest(child))
    return best
