def search_matrix(matrix: list[list[int]], target: int) -> bool:
    for row in matrix:
        for value in row:
            if value == target:
                return True
    return False
