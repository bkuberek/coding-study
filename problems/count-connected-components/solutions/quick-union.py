def count_components(n: int, edges: list[list[int]]) -> int:
    parent = list(range(n))  # parent[x] == x marks a root

    def find(x: int) -> int:
        while parent[x] != x:
            x = parent[x]
        return x

    components = n
    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_a] = root_b  # no balancing: trees can grow into long chains
            components -= 1
    return components
