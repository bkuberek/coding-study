def longest_increasing_path(matrix: list[list[int]]) -> int:
    rows, columns = len(matrix), len(matrix[0])
    # longest[r][c] is the longest increasing path starting at (r, c).
    longest = [[1] * columns for _ in range(rows)]
    # Every larger neighbor comes earlier in decreasing order of value, so its entry is final
    # when the cell is processed. Equal neighbors are never steps, so ties may go either way.
    order = sorted(
        ((r, c) for r in range(rows) for c in range(columns)),
        key=lambda cell: matrix[cell[0]][cell[1]],
        reverse=True,
    )
    for r, c in order:
        value = matrix[r][c]
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < columns and matrix[nr][nc] > value:
                longest[r][c] = max(longest[r][c], 1 + longest[nr][nc])
    return max(max(row) for row in longest)
