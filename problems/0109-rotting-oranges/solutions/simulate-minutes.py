FRESH, ROTTEN = 1, 2


def oranges_rotting(grid: list[list[int]]) -> int:
    rows, cols = len(grid), len(grid[0])
    minutes = 0
    while True:
        # Decide every change of this minute first, then apply them all: an orange that
        # turns now must not spread rot until the next minute.
        turning = [
            (r, c)
            for r in range(rows)
            for c in range(cols)
            if grid[r][c] == FRESH
            and any(
                0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == ROTTEN
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1))
            )
        ]
        if not turning:
            break
        for r, c in turning:
            grid[r][c] = ROTTEN
        minutes += 1
    fresh_left = any(cell == FRESH for row in grid for cell in row)
    return -1 if fresh_left else minutes
