def set_zeroes(matrix: list[list[int]]) -> None:
    # Find every row and column to clear before clearing anything.
    zero_rows: set[int] = set()
    zero_cols: set[int] = set()
    for r, row in enumerate(matrix):
        for c, value in enumerate(row):
            if value == 0:
                zero_rows.add(r)
                zero_cols.add(c)
    for r, row in enumerate(matrix):
        for c in range(len(row)):
            if r in zero_rows or c in zero_cols:
                row[c] = 0
