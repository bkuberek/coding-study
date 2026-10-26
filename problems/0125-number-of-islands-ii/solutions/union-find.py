STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def num_islands2(m: int, n: int, positions: list[list[int]]) -> list[int]:
    parent = list(range(m * n))  # cell r * n + c
    size = [1] * (m * n)  # size[r]: number of cells in the tree rooted at r
    land = [False] * (m * n)

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression: point the whole path at the root
            parent[x], x = root, parent[x]
        return root

    def union(a: int, b: int) -> bool:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return False
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a  # union by size: the smaller tree goes under the larger
        size[root_a] += size[root_b]
        return True

    islands = 0
    counts: list[int] = []
    for r, c in positions:
        cell = r * n + c
        if not land[cell]:
            land[cell] = True
            islands += 1  # a new island, until it merges with its neighbors
            for dr, dc in STEPS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n and land[nr * n + nc] and union(nr * n + nc, cell):
                    islands -= 1
        counts.append(islands)
    return counts
