from cs_support import TreeNode


def path_sum(root: TreeNode | None, target_sum: int) -> int:
    count = 0
    starts = [root] if root is not None else []
    while starts:
        start = starts.pop()
        # Walk every downward path from start, carrying the sum so far.
        pending = [(start, start.val)]
        while pending:
            node, total = pending.pop()
            if total == target_sum:
                count += 1
            for child in (node.left, node.right):
                if child is not None:
                    pending.append((child, total + child.val))
        starts.extend(child for child in (start.left, start.right) if child is not None)
    return count
