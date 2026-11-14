def search_matrix(matrix: list[list[int]], target: int) -> bool:
    columns = len(matrix[0])
    low, high = 0, len(matrix) * columns - 1
    while low <= high:
        middle = (low + high) // 2
        row, column = divmod(middle, columns)
        value = matrix[row][column]
        if value == target:
            return True
        if value < target:
            low = middle + 1
        else:
            high = middle - 1
    return False
