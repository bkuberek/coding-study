from collections import deque


def num_islands(grid: list[list[str]]) -> int:
    rows, cols = len(grid), len(grid[0])
    visited = [[False] * cols for _ in range(rows)]
    islands = 0
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] != "1" or visited[row][col]:
                continue
            islands += 1
            visited[row][col] = True
            queue = deque([(row, col)])
            while queue:
                r, c = queue.popleft()
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "1" and not visited[nr][nc]:
                        visited[nr][nc] = True
                        queue.append((nr, nc))
    return islands
