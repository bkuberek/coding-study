from collections import deque

FRESH, ROTTEN = 1, 2


def oranges_rotting(grid: list[list[int]]) -> int:
    rows, cols = len(grid), len(grid[0])
    queue: deque[tuple[int, int]] = deque()
    fresh = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == ROTTEN:
                queue.append((r, c))
            elif grid[r][c] == FRESH:
                fresh += 1
    minutes = 0
    # Each pass of the outer loop is one minute: it rots the whole current frontier.
    while queue and fresh > 0:
        minutes += 1
        for _ in range(len(queue)):
            r, c = queue.popleft()
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == FRESH:
                    grid[nr][nc] = ROTTEN
                    fresh -= 1
                    queue.append((nr, nc))
    return minutes if fresh == 0 else -1
