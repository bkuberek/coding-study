SAFE = "S"


def solve(board: list[list[str]]) -> None:
    rows, cols = len(board), len(board[0])
    # Every 'O' on the edge is safe; so is everything connected to one of them.
    stack = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if (r in (0, rows - 1) or c in (0, cols - 1)) and board[r][c] == "O"
    ]
    for r, c in stack:
        board[r][c] = SAFE
    while stack:
        r, c = stack.pop()
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] == "O":
                board[nr][nc] = SAFE
                stack.append((nr, nc))
    for row in board:
        for c, cell in enumerate(row):
            row[c] = "O" if cell == SAFE else "X"
