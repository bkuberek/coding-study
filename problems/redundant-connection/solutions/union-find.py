def find_redundant_connection(edges: list[list[int]]) -> list[int]:
    parent = list(range(len(edges) + 1))
    size = [1] * (len(edges) + 1)  # size[r]: number of nodes in the tree rooted at r

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression: point the whole path at the root
            parent[x], x = root, parent[x]
        return root

    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return [a, b]  # the ends are already connected: this edge closes the cycle
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a  # union by size: the smaller tree goes under the larger
        size[root_a] += size[root_b]
    return []
