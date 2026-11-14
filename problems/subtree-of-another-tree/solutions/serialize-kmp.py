from cs_support import TreeNode


def is_subtree(root: TreeNode | None, sub_root: TreeNode | None) -> bool:
    return _occurs(_tokens(sub_root), _tokens(root))


def _tokens(root: TreeNode | None) -> list[int | None]:
    """Pre-order values with None for every missing child: a unique description of the tree."""
    tokens: list[int | None] = []
    pending = [root]
    while pending:
        node = pending.pop()
        if node is None:
            tokens.append(None)
            continue
        tokens.append(node.val)
        pending.append(node.right)
        pending.append(node.left)
    return tokens


def _occurs(pattern: list[int | None], text: list[int | None]) -> bool:
    """Knuth-Morris-Pratt: does `pattern` occur as a contiguous block of `text`?"""
    border = [0] * len(pattern)
    length = 0
    for i in range(1, len(pattern)):
        while length and pattern[i] != pattern[length]:
            length = border[length - 1]
        if pattern[i] == pattern[length]:
            length += 1
        border[i] = length
    matched = 0
    for token in text:
        while matched and token != pattern[matched]:
            matched = border[matched - 1]
        if token == pattern[matched]:
            matched += 1
            if matched == len(pattern):
                return True
    return False
