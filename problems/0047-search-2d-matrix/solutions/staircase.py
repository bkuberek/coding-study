def search_matrix(matrix: list[list[int]], target: int) -> bool:
    # Everything left of the current cell in its row is smaller or equal; everything
    # below it in its column is larger or equal.
    row, column = 0, len(matrix[0]) - 1
    while row < len(matrix) and column >= 0:
        value = matrix[row][column]
        if value == target:
            return True
        if value > target:
            column -= 1
        else:
            row += 1
    return False
