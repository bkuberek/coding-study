def has_path(n: int, edges: list[list[int]], source: int, target: int) -> bool:
    parent = list(range(n))
    size = [1] * n

    def find(node: int) -> int:
        # Path halving: point every other node on the way up at its grandparent.
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            continue
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a
        size[root_a] += size[root_b]
    return find(source) == find(target)
