def min_path_sum(grid: list[list[int]]) -> int:
    rows, columns = len(grid), len(grid[0])
    unknown = -1
    cheapest = [[unknown] * columns for _ in range(rows)]

    def cheapest_to(row: int, column: int) -> int:
        if cheapest[row][column] != unknown:
            return cheapest[row][column]
        if row == 0 and column == 0:
            arrival = 0
        elif row == 0:
            arrival = cheapest_to(row, column - 1)
        elif column == 0:
            arrival = cheapest_to(row - 1, column)
        else:
            arrival = min(cheapest_to(row - 1, column), cheapest_to(row, column - 1))
        cheapest[row][column] = arrival + grid[row][column]
        return cheapest[row][column]

    return cheapest_to(rows - 1, columns - 1)
