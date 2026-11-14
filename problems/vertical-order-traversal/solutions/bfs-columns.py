from collections import defaultdict, deque

from cs_support import TreeNode


def vertical_order(root: TreeNode | None) -> list[list[int]]:
    if root is None:
        return []
    columns: dict[int, list[int]] = defaultdict(list)
    queue = deque([(root, 0)])
    while queue:
        node, column = queue.popleft()
        columns[column].append(node.val)
        if node.left is not None:
            queue.append((node.left, column - 1))
        if node.right is not None:
            queue.append((node.right, column + 1))
    # Columns form a contiguous range: every path from the root moves one column per step.
    return [columns[column] for column in range(min(columns), max(columns) + 1)]
