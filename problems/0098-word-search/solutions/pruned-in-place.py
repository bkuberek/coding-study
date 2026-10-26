from collections import Counter

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
USED = "#"


def exist(board: list[list[str]], word: str) -> bool:
    rows, cols = len(board), len(board[0])
    available = Counter(letter for row in board for letter in row)
    if any(available[letter] < needed for letter, needed in Counter(word).items()):
        return False
    # A walk read backwards is also a walk: start from whichever end is rarer on the board.
    if available[word[0]] > available[word[-1]]:
        word = word[::-1]

    def spells_from(r: int, c: int, k: int) -> bool:
        if board[r][c] != word[k]:
            return False
        if k == len(word) - 1:
            return True
        board[r][c] = USED
        found = any(
            0 <= r + dr < rows and 0 <= c + dc < cols and spells_from(r + dr, c + dc, k + 1)
            for dr, dc in STEPS
        )
        board[r][c] = word[k]
        return found

    return any(spells_from(r, c, 0) for r in range(rows) for c in range(cols))
