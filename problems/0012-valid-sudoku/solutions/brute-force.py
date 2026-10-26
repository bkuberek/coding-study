SIDE = 9
BOX = 3
EMPTY = "."


def is_valid_sudoku(board: list[list[str]]) -> bool:
    for row in range(SIDE):
        for column in range(SIDE):
            digit = board[row][column]
            if digit != EMPTY and _repeats(board, row, column, digit):
                return False
    return True


def _repeats(board: list[list[str]], row: int, column: int, digit: str) -> bool:
    """Whether another cell in the same row, column or box holds `digit`."""
    top, left = row - row % BOX, column - column % BOX
    for i in range(SIDE):
        if i != column and board[row][i] == digit:
            return True
        if i != row and board[i][column] == digit:
            return True
        box_row, box_column = top + i // BOX, left + i % BOX
        if (box_row, box_column) != (row, column) and board[box_row][box_column] == digit:
            return True
    return False
