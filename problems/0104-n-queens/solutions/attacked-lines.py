def solve_n_queens(n: int) -> list[list[str]]:
    boards: list[list[str]] = []
    queen_column: list[int] = []
    columns: set[int] = set()
    # Squares on one diagonal share row - col; on one anti-diagonal they share row + col.
    diagonals: set[int] = set()
    anti_diagonals: set[int] = set()

    def place(row: int) -> None:
        if row == n:
            boards.append(["." * c + "Q" + "." * (n - c - 1) for c in queen_column])
            return
        for col in range(n):
            if col in columns or row - col in diagonals or row + col in anti_diagonals:
                continue
            columns.add(col)
            diagonals.add(row - col)
            anti_diagonals.add(row + col)
            queen_column.append(col)
            place(row + 1)
            queen_column.pop()
            columns.remove(col)
            diagonals.remove(row - col)
            anti_diagonals.remove(row + col)

    place(0)
    return boards
