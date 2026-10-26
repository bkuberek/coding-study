from cs_support import TreeNode


def is_same_tree(p: TreeNode | None, q: TreeNode | None) -> bool:
    pending = [(p, q)]
    while pending:
        a, b = pending.pop()
        if a is None and b is None:
            continue
        if a is None or b is None or a.val != b.val:
            return False
        pending.append((a.right, b.right))
        pending.append((a.left, b.left))
    return True
