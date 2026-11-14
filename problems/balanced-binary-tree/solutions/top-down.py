from cs_support import TreeNode


def is_balanced(root: TreeNode | None) -> bool:
    if root is None:
        return True
    return abs(_height(root.left) - _height(root.right)) <= 1 and is_balanced(root.left) and is_balanced(root.right)


def _height(node: TreeNode | None) -> int:
    if node is None:
        return 0
    return 1 + max(_height(node.left), _height(node.right))
