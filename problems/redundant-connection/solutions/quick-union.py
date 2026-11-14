def find_redundant_connection(edges: list[list[int]]) -> list[int]:
    parent = list(range(len(edges) + 1))  # parent[x] == x marks a root

    def find(x: int) -> int:
        while parent[x] != x:
            x = parent[x]
        return x

    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return [a, b]  # the ends are already connected: this edge closes the cycle
        parent[root_a] = root_b  # no balancing: trees can grow into long chains
    return []
