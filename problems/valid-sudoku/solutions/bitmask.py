SIDE = 9
BOX = 3
EMPTY = "."


def is_valid_sudoku(board: list[list[str]]) -> bool:
    # Bit d - 1 of a mask is set once digit d has been seen in that row, column or box.
    rows = [0] * SIDE
    columns = [0] * SIDE
    boxes = [0] * SIDE
    for row in range(SIDE):
        for column in range(SIDE):
            digit = board[row][column]
            if digit == EMPTY:
                continue
            bit = 1 << (int(digit) - 1)
            box = (row // BOX) * BOX + column // BOX
            if (rows[row] | columns[column] | boxes[box]) & bit:
                return False
            rows[row] |= bit
            columns[column] |= bit
            boxes[box] |= bit
    return True
