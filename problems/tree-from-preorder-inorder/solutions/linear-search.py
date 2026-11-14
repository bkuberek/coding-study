from cs_support import TreeNode


def build_tree(preorder: list[int], inorder: list[int]) -> TreeNode | None:
    def build(pre_start: int, in_start: int, size: int) -> TreeNode | None:
        """Tree of the `size` values at preorder[pre_start:] and inorder[in_start:]."""
        if size == 0:
            return None
        value = preorder[pre_start]
        split = inorder.index(value, in_start, in_start + size)
        left_size = split - in_start
        node = TreeNode(value)
        node.left = build(pre_start + 1, in_start, left_size)
        node.right = build(pre_start + 1 + left_size, split + 1, size - left_size - 1)
        return node

    return build(0, 0, len(preorder))
