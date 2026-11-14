from cs_support import TreeNode


def is_valid_bst(root: TreeNode | None) -> bool:
    stack: list[TreeNode] = []
    node = root
    previous: int | None = None
    while stack or node is not None:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        if previous is not None and node.val <= previous:
            return False
        previous = node.val
        node = node.right
    return True
