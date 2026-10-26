from cs_support import TreeNode


def max_path_sum(root: TreeNode | None) -> int:
    best = root.val

    def gain(node: TreeNode | None) -> int:
        """Best downward path sum from `node`, recording the best path turning at it."""
        nonlocal best
        if node is None:
            return 0
        left = max(0, gain(node.left))
        right = max(0, gain(node.right))
        best = max(best, node.val + left + right)
        return node.val + max(left, right)

    gain(root)
    return best
