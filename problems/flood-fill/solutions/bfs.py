from collections import deque


def flood_fill(grid: list[list[int]], row: int, col: int, new_color: int) -> list[list[int]]:
    old_color = grid[row][col]
    if old_color == new_color:
        return grid
    rows, cols = len(grid), len(grid[0])
    grid[row][col] = new_color
    queue = deque([(row, col)])
    while queue:
        r, c = queue.popleft()
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            # Repaint when a square is queued, so it can never be queued twice.
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == old_color:
                grid[nr][nc] = new_color
                queue.append((nr, nc))
    return grid
