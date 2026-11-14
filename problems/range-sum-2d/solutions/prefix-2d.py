class NumMatrix:
    def __init__(self, matrix: list[list[int]]) -> None:
        cols = len(matrix[0])
        # prefix[r][c] is the sum of the sub-grid matrix[:r][:c]; row 0 and column 0 are zeros.
        self.prefix = [[0] * (cols + 1)]
        for cells in matrix:
            above = self.prefix[-1]
            row = [0] * (cols + 1)
            running = 0
            for c, value in enumerate(cells):
                running += value
                row[c + 1] = above[c + 1] + running
            self.prefix.append(row)

    def sum_region(self, row1: int, col1: int, row2: int, col2: int) -> int:
        p = self.prefix
        return p[row2 + 1][col2 + 1] - p[row1][col2 + 1] - p[row2 + 1][col1] + p[row1][col1]
