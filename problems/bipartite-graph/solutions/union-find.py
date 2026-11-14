def is_bipartite(graph: list[list[int]]) -> bool:
    parent = list(range(len(graph)))
    size = [1] * len(graph)

    def find(node: int) -> int:
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a
        size[root_a] += size[root_b]

    # All neighbors of a node must share a team, so they go into one group.
    for neighbors in graph:
        for neighbor in neighbors[1:]:
            union(neighbors[0], neighbor)
    # A split exists exactly when no edge has both ends in one group.
    return all(find(node) != find(neighbor) for node, neighbors in enumerate(graph) for neighbor in neighbors)
