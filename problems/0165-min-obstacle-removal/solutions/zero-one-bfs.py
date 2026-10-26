from collections import deque


def minimum_obstacles(grid: list[list[int]]) -> int:
    rows, cols = len(grid), len(grid[0])
    unreached = rows * cols
    removals = [[unreached] * cols for _ in range(rows)]
    removals[0][0] = 0
    # The deque stays sorted by removals: zero-cost steps go to the front, one-cost steps
    # to the back, so its two ends never differ by more than one.
    queue = deque([(0, 0)])
    while queue:
        r, c = queue.popleft()
        cost = removals[r][c]
        if (r, c) == (rows - 1, cols - 1):
            return cost
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols and cost + grid[nr][nc] < removals[nr][nc]:
                removals[nr][nc] = cost + grid[nr][nc]
                if grid[nr][nc] == 0:
                    queue.appendleft((nr, nc))
                else:
                    queue.append((nr, nc))
    return removals[rows - 1][cols - 1]
