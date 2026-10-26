from cs_support import TreeNode


def leaf_values(root: TreeNode | None, leaves: list[int] | None = None) -> list[int]:
    if leaves is None:
        leaves = []
    if root is None:
        return leaves
    if root.left is None and root.right is None:
        leaves.append(root.val)
    leaf_values(root.left, leaves)
    leaf_values(root.right, leaves)
    return leaves
