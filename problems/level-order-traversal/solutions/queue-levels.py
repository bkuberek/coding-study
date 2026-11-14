from collections import deque

from cs_support import TreeNode


def level_order(root: TreeNode | None) -> list[list[int]]:
    levels: list[list[int]] = []
    queue = deque([root] if root is not None else [])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        levels.append(level)
    return levels
