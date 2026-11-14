"""Debug: Grid Aliasing. Some tests fail: find the bug and fix it."""

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def burn_times(grid: list[list[int]]) -> list[list[int]]:
    rows, cols = len(grid), len(grid[0])
    times = [[-1] * cols] * rows
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                times[r][c] = 0

    current = grid
    minute = 0
    spreading = True
    while spreading:
        minute += 1
        spreading = False
        upcoming = current.copy()
        for r in range(rows):
            for c in range(cols):
                if current[r][c] != 2:
                    continue
                for dr, dc in STEPS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and current[nr][nc] == 1:
                        upcoming[nr][nc] = 2
                        times[nr][nc] = minute
                        spreading = True
        current = upcoming
    return times
