def maximal_square(matrix: list[list[str]]) -> int:
    rows, columns = len(matrix), len(matrix[0])
    # side[r + 1][c + 1] is the largest all-ones square with its bottom-right corner at (r, c);
    # row 0 and column 0 are a border of zeros.
    side = [[0] * (columns + 1) for _ in range(rows + 1)]
    best = 0
    for r in range(rows):
        for c in range(columns):
            if matrix[r][c] == "1":
                side[r + 1][c + 1] = 1 + min(side[r][c + 1], side[r + 1][c], side[r][c])
                best = max(best, side[r + 1][c + 1])
    return best * best
