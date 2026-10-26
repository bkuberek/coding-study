from collections import deque

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def burn_times(grid: list[list[int]]) -> list[list[int]]:
    rows, cols = len(grid), len(grid[0])
    times = [[-1] * cols for _ in range(rows)]
    queue: deque[tuple[int, int]] = deque()
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                times[r][c] = 0
                queue.append((r, c))
    while queue:
        r, c = queue.popleft()
        for dr, dc in STEPS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1 and times[nr][nc] == -1:
                times[nr][nc] = times[r][c] + 1
                queue.append((nr, nc))
    return times
