def solve_n_queens(n: int) -> list[list[str]]:
    full = (1 << n) - 1
    boards: list[list[str]] = []
    queen_column: list[int] = []

    def place(columns: int, diagonals: int, anti_diagonals: int) -> None:
        """Each mask marks the squares of the current row attacked along one kind of line."""
        if columns == full:
            boards.append(["." * c + "Q" + "." * (n - c - 1) for c in queen_column])
            return
        free = full & ~(columns | diagonals | anti_diagonals)
        while free:
            bit = free & -free  # lowest free square
            free ^= bit
            queen_column.append(bit.bit_length() - 1)
            # Moving one row down shifts each diagonal attack one column over.
            place(columns | bit, (diagonals | bit) << 1 & full, (anti_diagonals | bit) >> 1)
            queen_column.pop()

    place(0, 0, 0)
    return boards
