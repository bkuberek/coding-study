from cs_support import TreeNode


def has_path_sum(root: TreeNode | None, target: int) -> bool:
    if root is None:
        return False
    remaining = target - root.val
    if root.left is None and root.right is None:
        return remaining == 0
    return has_path_sum(root.left, remaining) or has_path_sum(root.right, remaining)
