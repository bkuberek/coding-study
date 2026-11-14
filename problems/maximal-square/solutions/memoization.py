def maximal_square(matrix: list[list[str]]) -> int:
    rows, columns = len(matrix), len(matrix[0])
    # side[r][c] caches the largest all-ones square with its top-left corner at (r, c);
    # -1 is unknown.
    side = [[-1] * columns for _ in range(rows)]

    def largest(r: int, c: int) -> int:
        if r == rows or c == columns or matrix[r][c] == "0":
            return 0
        if side[r][c] < 0:
            side[r][c] = 1 + min(largest(r + 1, c), largest(r, c + 1), largest(r + 1, c + 1))
        return side[r][c]

    best = max(largest(r, c) for r in range(rows) for c in range(columns))
    return best * best
