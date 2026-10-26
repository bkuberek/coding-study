def maximal_rectangle(matrix: list[list[str]]) -> int:
    rows, columns = len(matrix), len(matrix[0])
    # width[r][c] is the number of consecutive ones ending at (r, c) in row r.
    width = [[0] * columns for _ in range(rows)]
    best = 0
    for r in range(rows):
        for c in range(columns):
            if matrix[r][c] == "0":
                continue
            width[r][c] = width[r][c - 1] + 1 if c > 0 else 1
            # Rectangles with bottom-right corner (r, c): extend upwards one row at a time; the
            # rectangle is as wide as the narrowest row it spans.
            narrowest = width[r][c]
            for top in range(r, -1, -1):
                narrowest = min(narrowest, width[top][c])
                if narrowest == 0:
                    break
                best = max(best, narrowest * (r - top + 1))
    return best
