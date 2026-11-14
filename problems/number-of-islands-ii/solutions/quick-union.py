STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def num_islands2(m: int, n: int, positions: list[list[int]]) -> list[int]:
    parent = list(range(m * n))  # cell r * n + c; parent[x] == x marks a root
    land = [False] * (m * n)

    def find(x: int) -> int:
        while parent[x] != x:
            x = parent[x]
        return x

    islands = 0
    counts: list[int] = []
    for r, c in positions:
        cell = r * n + c
        if not land[cell]:
            land[cell] = True
            islands += 1  # a new island, until it merges with its neighbors
            for dr, dc in STEPS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n and land[nr * n + nc]:
                    root_neighbor, root_cell = find(nr * n + nc), find(cell)
                    if root_neighbor != root_cell:
                        parent[root_neighbor] = root_cell  # no balancing: chains can grow
                        islands -= 1
        counts.append(islands)
    return counts
