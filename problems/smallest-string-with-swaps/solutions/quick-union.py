from collections import defaultdict


def smallest_string_with_swaps(s: str, pairs: list[list[int]]) -> str:
    parent = list(range(len(s)))  # parent[x] == x marks a root

    def find(x: int) -> int:
        while parent[x] != x:
            x = parent[x]
        return x

    for a, b in pairs:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_a] = root_b  # no balancing: trees can grow into long chains

    # Positions come out of range() in increasing order, so each group's list is sorted.
    groups: defaultdict[int, list[int]] = defaultdict(list)
    for position in range(len(s)):
        groups[find(position)].append(position)
    letters = list(s)
    for positions in groups.values():
        for position, letter in zip(positions, sorted(s[p] for p in positions)):
            letters[position] = letter
    return "".join(letters)
