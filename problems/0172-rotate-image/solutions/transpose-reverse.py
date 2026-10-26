def rotate(matrix: list[list[int]]) -> None:
    n = len(matrix)
    # Reflect across the main diagonal, then mirror every row left to right.
    for r in range(n):
        for c in range(r + 1, n):
            matrix[r][c], matrix[c][r] = matrix[c][r], matrix[r][c]
    for row in matrix:
        row.reverse()
