def maximal_square(matrix: list[list[str]]) -> int:
    # side[c + 1] is the largest square ending at column c of the current row (before the
    # update: of the row above); side[0] is a border of zeros.
    side = [0] * (len(matrix[0]) + 1)
    best = 0
    for row in matrix:
        diagonal = 0  # the row-above value of the previous column, saved before it is overwritten
        for c, cell in enumerate(row, start=1):
            above = side[c]
            side[c] = 1 + min(above, side[c - 1], diagonal) if cell == "1" else 0
            best = max(best, side[c])
            diagonal = above
    return best * best
