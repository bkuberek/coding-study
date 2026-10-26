def set_zeroes(matrix: list[list[int]]) -> None:
    rows, cols = len(matrix), len(matrix[0])
    # matrix[r][0] marks row r (matrix[0][0] marks row 0) and matrix[0][c] marks column c
    # for c >= 1; column 0 needs its own flag, because matrix[0][0] is taken.
    first_col_has_zero = False
    for r in range(rows):
        if matrix[r][0] == 0:
            first_col_has_zero = True
        for c in range(1, cols):
            if matrix[r][c] == 0:
                matrix[r][0] = 0
                matrix[0][c] = 0
    # Bottom-up, so the markers in row 0 are read before row 0 itself is cleared.
    for r in range(rows - 1, -1, -1):
        for c in range(cols - 1, 0, -1):
            if matrix[r][0] == 0 or matrix[0][c] == 0:
                matrix[r][c] = 0
        if first_col_has_zero:
            matrix[r][0] = 0
