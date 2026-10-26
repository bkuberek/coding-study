def count_components(n: int, edges: list[list[int]]) -> int:
    parent = list(range(n))
    size = [1] * n  # size[r]: number of nodes in the tree rooted at r

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression: point the whole path at the root
            parent[x], x = root, parent[x]
        return root

    components = n
    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            continue
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a  # union by size: the smaller tree goes under the larger
        size[root_a] += size[root_b]
        components -= 1
    return components
