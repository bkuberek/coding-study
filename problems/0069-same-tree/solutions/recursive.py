from cs_support import TreeNode


def is_same_tree(p: TreeNode | None, q: TreeNode | None) -> bool:
    if p is None or q is None:
        return p is q
    return p.val == q.val and is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)
