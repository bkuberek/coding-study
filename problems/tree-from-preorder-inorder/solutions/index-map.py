from cs_support import TreeNode


def build_tree(preorder: list[int], inorder: list[int]) -> TreeNode | None:
    position = {value: index for index, value in enumerate(inorder)}
    next_root = 0

    def build(low: int, high: int) -> TreeNode | None:
        """Tree whose in-order walk is inorder[low:high]; its root is the next pre-order value."""
        nonlocal next_root
        if low == high:
            return None
        value = preorder[next_root]
        next_root += 1
        split = position[value]
        node = TreeNode(value)
        node.left = build(low, split)
        node.right = build(split + 1, high)
        return node

    return build(0, len(inorder))
