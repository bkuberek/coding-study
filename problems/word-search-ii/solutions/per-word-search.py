USED = "#"
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def find_words(board: list[list[str]], words: list[str]) -> list[str]:
    return [word for word in words if _on_board(board, word)]


def _on_board(board: list[list[str]], word: str) -> bool:
    rows, cols = len(board), len(board[0])

    def trace(row: int, col: int, position: int) -> bool:
        """Can word[position:] be spelled starting at this cell?"""
        if board[row][col] != word[position]:
            return False
        if position == len(word) - 1:
            return True
        board[row][col] = USED
        found = any(
            0 <= row + dr < rows and 0 <= col + dc < cols and trace(row + dr, col + dc, position + 1)
            for dr, dc in STEPS
        )
        board[row][col] = word[position]
        return found

    return any(trace(row, col, 0) for row in range(rows) for col in range(cols))
