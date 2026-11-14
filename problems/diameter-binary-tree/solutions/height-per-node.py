from cs_support import TreeNode


def diameter_of_binary_tree(root: TreeNode | None) -> int:
    if root is None:
        return 0
    turning_here = _height(root.left) + _height(root.right)
    return max(turning_here, diameter_of_binary_tree(root.left), diameter_of_binary_tree(root.right))


def _height(node: TreeNode | None) -> int:
    """Number of nodes on the longest downward path from `node`."""
    if node is None:
        return 0
    return 1 + max(_height(node.left), _height(node.right))
