STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def exist(board: list[list[str]], word: str) -> bool:
    rows, cols = len(board), len(board[0])
    visited = [[False] * cols for _ in range(rows)]

    def spells_from(r: int, c: int, k: int) -> bool:
        """Whether word[k:] can be spelled by a walk that starts at (r, c)."""
        if not (0 <= r < rows and 0 <= c < cols) or visited[r][c] or board[r][c] != word[k]:
            return False
        if k == len(word) - 1:
            return True
        visited[r][c] = True
        found = any(spells_from(r + dr, c + dc, k + 1) for dr, dc in STEPS)
        visited[r][c] = False
        return found

    return any(spells_from(r, c, 0) for r in range(rows) for c in range(cols))
