from cs_support import TreeNode


class BSTIterator:
    def __init__(self, root: TreeNode | None) -> None:
        # Nodes whose left subtree is finished (or about to be) and that are not returned yet.
        self.stack: list[TreeNode] = []
        self._push_left_spine(root)

    def _push_left_spine(self, node: TreeNode | None) -> None:
        while node is not None:
            self.stack.append(node)
            node = node.left

    def next(self) -> int:
        node = self.stack.pop()
        self._push_left_spine(node.right)
        return node.val

    def has_next(self) -> bool:
        return bool(self.stack)
