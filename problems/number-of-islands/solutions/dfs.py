def num_islands(grid: list[list[str]]) -> int:
    rows, cols = len(grid), len(grid[0])
    islands = 0
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] != "1":
                continue
            islands += 1
            # Sink the island: every land square becomes water as soon as it is discovered,
            # so it is pushed at most once and never counted again.
            grid[row][col] = "0"
            stack = [(row, col)]
            while stack:
                r, c = stack.pop()
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == "1":
                        grid[nr][nc] = "0"
                        stack.append((nr, nc))
    return islands
