from itertools import groupby

from cs_support import TreeNode


def vertical_order(root: TreeNode | None) -> list[list[int]]:
    entries: list[tuple[int, int, int]] = []  # (column, row, value) in pre-order

    def visit(node: TreeNode | None, column: int, row: int) -> None:
        if node is None:
            return
        entries.append((column, row, node.val))
        visit(node.left, column - 1, row + 1)
        visit(node.right, column + 1, row + 1)

    visit(root, 0, 0)
    # A stable sort keeps pre-order (left to right) among nodes with the same column and row.
    entries.sort(key=lambda entry: (entry[0], entry[1]))
    return [[value for _, _, value in group] for _, group in groupby(entries, key=lambda entry: entry[0])]
