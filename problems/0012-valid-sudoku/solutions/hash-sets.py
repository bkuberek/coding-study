SIDE = 9
BOX = 3
EMPTY = "."


def is_valid_sudoku(board: list[list[str]]) -> bool:
    rows = [set() for _ in range(SIDE)]
    columns = [set() for _ in range(SIDE)]
    boxes = [set() for _ in range(SIDE)]
    for row in range(SIDE):
        for column in range(SIDE):
            digit = board[row][column]
            if digit == EMPTY:
                continue
            box = (row // BOX) * BOX + column // BOX
            if digit in rows[row] or digit in columns[column] or digit in boxes[box]:
                return False
            rows[row].add(digit)
            columns[column].add(digit)
            boxes[box].add(digit)
    return True
