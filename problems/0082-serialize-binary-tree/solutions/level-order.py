from collections import deque

from cs_support import TreeNode

MISSING = "#"
SEPARATOR = ","


def serialize_deserialize(root: TreeNode | None) -> TreeNode | None:
    return deserialize(serialize(root))


def serialize(root: TreeNode | None) -> str:
    tokens: list[str] = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            tokens.append(MISSING)
            continue
        tokens.append(str(node.val))
        queue.append(node.left)
        queue.append(node.right)
    return SEPARATOR.join(tokens)


def deserialize(data: str) -> TreeNode | None:
    tokens = data.split(SEPARATOR)
    if tokens[0] == MISSING:
        return None
    root = TreeNode(int(tokens[0]))
    queue = deque([root])
    position = 1
    # Every node was written with exactly two child tokens, in queue order.
    while queue:
        node = queue.popleft()
        left, right = tokens[position], tokens[position + 1]
        position += 2
        if left != MISSING:
            node.left = TreeNode(int(left))
            queue.append(node.left)
        if right != MISSING:
            node.right = TreeNode(int(right))
            queue.append(node.right)
    return root
