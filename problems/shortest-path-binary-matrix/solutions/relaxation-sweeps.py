STEPS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]


def shortest_path_binary_matrix(grid: list[list[int]]) -> int:
    n = len(grid)
    if grid[0][0] == 1 or grid[n - 1][n - 1] == 1:
        return -1
    unreached = n * n + 1
    dist = [[unreached] * n for _ in range(n)]
    dist[0][0] = 1
    order = [(r, c) for r in range(n) for c in range(n)]
    changed = True
    while changed:
        changed = False
        # Each sweep lets every open cell take the best distance offered by a neighbor.
        for r, c in order:
            if grid[r][c] == 1:
                continue
            for dr, dc in STEPS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and dist[nr][nc] + 1 < dist[r][c]:
                    dist[r][c] = dist[nr][nc] + 1
                    changed = True
        # Alternating the scan direction lets improvements travel both ways quickly.
        order.reverse()
    best = dist[n - 1][n - 1]
    return best if best < unreached else -1
