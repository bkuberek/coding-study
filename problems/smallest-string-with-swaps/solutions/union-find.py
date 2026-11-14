from collections import defaultdict


def smallest_string_with_swaps(s: str, pairs: list[list[int]]) -> str:
    parent = list(range(len(s)))
    size = [1] * len(s)  # size[r]: number of positions in the tree rooted at r

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression: point the whole path at the root
            parent[x], x = root, parent[x]
        return root

    for a, b in pairs:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            continue
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a  # union by size: the smaller tree goes under the larger
        size[root_a] += size[root_b]

    # Positions come out of range() in increasing order, so each group's list is sorted.
    groups: defaultdict[int, list[int]] = defaultdict(list)
    for position in range(len(s)):
        groups[find(position)].append(position)
    letters = list(s)
    for positions in groups.values():
        for position, letter in zip(positions, sorted(s[p] for p in positions)):
            letters[position] = letter
    return "".join(letters)
