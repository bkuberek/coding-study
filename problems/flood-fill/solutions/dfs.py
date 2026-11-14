def flood_fill(grid: list[list[int]], row: int, col: int, new_color: int) -> list[list[int]]:
    old_color = grid[row][col]
    if old_color == new_color:
        # Nothing to change. Without this check the fill below would never stop, because
        # a repainted square would still look like part of the region.
        return grid
    rows, cols = len(grid), len(grid[0])

    def paint(r: int, c: int) -> None:
        if not (0 <= r < rows and 0 <= c < cols) or grid[r][c] != old_color:
            return
        grid[r][c] = new_color
        paint(r + 1, c)
        paint(r - 1, c)
        paint(r, c + 1)
        paint(r, c - 1)

    paint(row, col)
    return grid
