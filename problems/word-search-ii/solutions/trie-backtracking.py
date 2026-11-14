USED = "#"
WORD = "$"  # key of the complete word stored at the node where it ends
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def find_words(board: list[list[str]], words: list[str]) -> list[str]:
    root: dict = {}
    for word in words:
        node = root
        for letter in word:
            node = node.setdefault(letter, {})
        node[WORD] = word
    rows, cols = len(board), len(board[0])
    found: list[str] = []

    def explore(row: int, col: int, parent: dict) -> None:
        letter = board[row][col]
        node = parent.get(letter)
        if node is None:
            return
        word = node.pop(WORD, None)
        if word is not None:
            found.append(word)
        board[row][col] = USED
        for dr, dc in STEPS:
            r, c = row + dr, col + dc
            if 0 <= r < rows and 0 <= c < cols:
                explore(r, c, node)
        board[row][col] = letter

    for row in range(rows):
        for col in range(cols):
            explore(row, col, root)
    return found
