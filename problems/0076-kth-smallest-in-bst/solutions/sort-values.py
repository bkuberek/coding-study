from cs_support import TreeNode


def kth_smallest(root: TreeNode | None, k: int) -> int:
    values: list[int] = []
    pending = [root]
    while pending:
        node = pending.pop()
        if node is not None:
            values.append(node.val)
            pending.append(node.left)
            pending.append(node.right)
    values.sort()
    return values[k - 1]
