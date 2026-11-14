from cs_support import TreeNode


class BSTIterator:
    def __init__(self, root: TreeNode | None) -> None:
        self.values: list[int] = []
        self._collect(root)
        self.position = 0

    def _collect(self, node: TreeNode | None) -> None:
        if node is not None:
            self._collect(node.left)
            self.values.append(node.val)
            self._collect(node.right)

    def next(self) -> int:
        value = self.values[self.position]
        self.position += 1
        return value

    def has_next(self) -> bool:
        return self.position < len(self.values)
