from collections import deque

from cs_support import TreeNode


def max_depth(root: TreeNode | None) -> int:
    level = deque([root] if root is not None else [])
    depth = 0
    while level:
        depth += 1
        # Drain exactly the nodes of the current level; their children form the next one.
        for _ in range(len(level)):
            node = level.popleft()
            if node.left is not None:
                level.append(node.left)
            if node.right is not None:
                level.append(node.right)
    return depth
