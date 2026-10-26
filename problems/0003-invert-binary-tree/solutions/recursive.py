from cs_support import TreeNode


def invert_tree(root: TreeNode | None) -> TreeNode | None:
    if root is None:
        return None
    root.left, root.right = invert_tree(root.right), invert_tree(root.left)
    return root
