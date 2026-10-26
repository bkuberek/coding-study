from collections import deque

from cs_support import TreeNode


def invert_tree(root: TreeNode | None) -> TreeNode | None:
    pending = deque([root] if root is not None else [])
    while pending:
        node = pending.popleft()
        node.left, node.right = node.right, node.left
        if node.left is not None:
            pending.append(node.left)
        if node.right is not None:
            pending.append(node.right)
    return root
