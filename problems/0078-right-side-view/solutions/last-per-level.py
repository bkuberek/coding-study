from collections import deque

from cs_support import TreeNode


def right_side_view(root: TreeNode | None) -> list[int]:
    view: list[int] = []
    queue = deque([root] if root is not None else [])
    while queue:
        # The node at the back of the queue is the last one of the current level.
        view.append(queue[-1].val)
        for _ in range(len(queue)):
            node = queue.popleft()
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
    return view
