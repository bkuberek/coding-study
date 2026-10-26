"""Debug: Recursion Base Case. Some tests fail: find the bug and fix it."""

from cs_support import TreeNode


def has_path_sum(root: TreeNode | None, target: int) -> bool:
    if root is None:
        return target == 0
    remaining = target - root.val
    return has_path_sum(root.left, remaining) or has_path_sum(root.right, remaining)
