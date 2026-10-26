from cs_support import TreeNode


def is_subtree(root: TreeNode | None, sub_root: TreeNode | None) -> bool:
    if root is None:
        return False
    return _same(root, sub_root) or is_subtree(root.left, sub_root) or is_subtree(root.right, sub_root)


def _same(a: TreeNode | None, b: TreeNode | None) -> bool:
    if a is None or b is None:
        return a is b
    return a.val == b.val and _same(a.left, b.left) and _same(a.right, b.right)
