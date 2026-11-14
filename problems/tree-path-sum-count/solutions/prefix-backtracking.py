from collections import Counter

from cs_support import TreeNode


def path_sum(root: TreeNode | None, target_sum: int) -> int:
    # on_path[s] counts the prefixes of the current root path whose sum is s.
    on_path = Counter({0: 1})

    def count_below(node: TreeNode | None, total: int) -> int:
        if node is None:
            return 0
        total += node.val
        found = on_path[total - target_sum]
        on_path[total] += 1
        found += count_below(node.left, total) + count_below(node.right, total)
        on_path[total] -= 1  # leave the subtree: its prefix is no longer on the path
        return found

    return count_below(root, 0)
