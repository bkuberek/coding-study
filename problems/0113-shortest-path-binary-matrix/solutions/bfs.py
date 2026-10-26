from collections import deque

STEPS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]


def shortest_path_binary_matrix(grid: list[list[int]]) -> int:
    n = len(grid)
    if grid[0][0] == 1 or grid[n - 1][n - 1] == 1:
        return -1
    dist = [[0] * n for _ in range(n)]
    dist[0][0] = 1
    queue = deque([(0, 0)])
    while queue:
        r, c = queue.popleft()
        if (r, c) == (n - 1, n - 1):
            return dist[r][c]
        for dr, dc in STEPS:
            nr, nc = r + dr, c + dc
            # dist 0 means "not reached yet": every reached cell has length at least 1.
            if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0 and dist[nr][nc] == 0:
                dist[nr][nc] = dist[r][c] + 1
                queue.append((nr, nc))
    return -1
