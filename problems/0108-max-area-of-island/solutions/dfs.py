def max_area_of_island(grid: list[list[int]]) -> int:
    rows, cols = len(grid), len(grid[0])
    seen = [[False] * cols for _ in range(rows)]
    best = 0
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] != 1 or seen[row][col]:
                continue
            seen[row][col] = True
            stack = [(row, col)]
            area = 0
            while stack:
                r, c = stack.pop()
                area += 1
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1 and not seen[nr][nc]:
                        seen[nr][nc] = True
                        stack.append((nr, nc))
            best = max(best, area)
    return best
