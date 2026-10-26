from cs_support import TreeNode


def right_side_view(root: TreeNode | None) -> list[int]:
    view: list[int] = []

    def visit(node: TreeNode | None, depth: int) -> None:
        if node is None:
            return
        if depth == len(view):
            view.append(node.val)
        visit(node.right, depth + 1)
        visit(node.left, depth + 1)

    visit(root, 0)
    return view
