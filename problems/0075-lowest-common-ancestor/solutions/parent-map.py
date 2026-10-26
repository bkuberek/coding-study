from cs_support import TreeNode


def lowest_common_ancestor(root: TreeNode, p: TreeNode, q: TreeNode) -> TreeNode:
    # Nodes hash by identity, so they can be dictionary keys directly.
    parent: dict[TreeNode, TreeNode | None] = {root: None}
    pending = [root]
    while p not in parent or q not in parent:
        current = pending.pop()
        for child in (current.left, current.right):
            if child is not None:
                parent[child] = current
                pending.append(child)
    ancestors_of_p: set[TreeNode] = set()
    node: TreeNode | None = p
    while node is not None:
        ancestors_of_p.add(node)
        node = parent[node]
    node = q
    while node not in ancestors_of_p:
        node = parent[node]
    return node
