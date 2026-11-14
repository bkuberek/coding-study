def min_path_sum(grid: list[list[int]]) -> int:
    rows, columns = len(grid), len(grid[0])
    # cheapest[r][c]: the smallest total toll of any route from the top-left block to block (r, c).
    cheapest = [[0] * columns for _ in range(rows)]
    for row in range(rows):
        for column in range(columns):
            if row == 0 and column == 0:
                arrival = 0
            elif row == 0:
                arrival = cheapest[row][column - 1]
            elif column == 0:
                arrival = cheapest[row - 1][column]
            else:
                arrival = min(cheapest[row - 1][column], cheapest[row][column - 1])
            cheapest[row][column] = arrival + grid[row][column]
    return cheapest[rows - 1][columns - 1]
