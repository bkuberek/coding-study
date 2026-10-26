def min_cost_connect_points(points: list[list[int]]) -> int:
    n = len(points)
    pairs = sorted(
        (abs(points[i][0] - points[j][0]) + abs(points[i][1] - points[j][1]), i, j)
        for i in range(n)
        for j in range(i + 1, n)
    )
    parent = list(range(n))

    def find(node: int) -> int:
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    total = 0
    cables = 0
    # Take pairs from cheapest to most expensive, keeping each one that joins two groups.
    for cost, i, j in pairs:
        if cables == n - 1:
            break
        root_i, root_j = find(i), find(j)
        if root_i != root_j:
            parent[root_i] = root_j
            total += cost
            cables += 1
    return total
