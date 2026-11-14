def solve_n_queens(n: int) -> list[list[str]]:
    boards: list[list[str]] = []
    # queen_column[r] is the column of the queen in row r, for the rows placed so far.
    queen_column: list[int] = []

    def is_safe(row: int, col: int) -> bool:
        return all(
            col != other_col and abs(col - other_col) != row - other_row
            for other_row, other_col in enumerate(queen_column)
        )

    def place(row: int) -> None:
        if row == n:
            boards.append(["." * c + "Q" + "." * (n - c - 1) for c in queen_column])
            return
        for col in range(n):
            if is_safe(row, col):
                queen_column.append(col)
                place(row + 1)
                queen_column.pop()

    place(0)
    return boards
