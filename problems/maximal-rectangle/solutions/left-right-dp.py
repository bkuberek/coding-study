def maximal_rectangle(matrix: list[list[str]]) -> int:
    columns = len(matrix[0])
    # For the current row and each column c: height[c] consecutive ones end here in column c,
    # and the rectangle of that height through column c spans columns left[c] .. right[c] - 1.
    height = [0] * columns
    left = [0] * columns
    right = [columns] * columns
    best = 0
    for row in matrix:
        boundary = 0  # first column after the last zero seen in this row
        for c in range(columns):
            if row[c] == "1":
                height[c] += 1
                left[c] = max(left[c], boundary)
            else:
                height[c], left[c], boundary = 0, 0, c + 1
        boundary = columns  # the last zero seen from the right
        for c in range(columns - 1, -1, -1):
            if row[c] == "1":
                right[c] = min(right[c], boundary)
            else:
                right[c], boundary = columns, c
        for c in range(columns):
            best = max(best, height[c] * (right[c] - left[c]))
    return best
