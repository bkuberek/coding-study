def rotate(matrix: list[list[int]]) -> None:
    n = len(matrix)
    # Row r of the rotated image is column r of the original, read from bottom to top.
    rotated = [[matrix[n - 1 - c][r] for c in range(n)] for r in range(n)]
    matrix[:] = rotated
