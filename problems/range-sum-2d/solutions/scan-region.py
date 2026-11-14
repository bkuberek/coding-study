class NumMatrix:
    def __init__(self, matrix: list[list[int]]) -> None:
        self.matrix = matrix

    def sum_region(self, row1: int, col1: int, row2: int, col2: int) -> int:
        total = 0
        for row in range(row1, row2 + 1):
            cells = self.matrix[row]
            for col in range(col1, col2 + 1):
                total += cells[col]
        return total
