"""Seeded inputs for word-search: small boards over few letters, so partial matches abound.

The word length is n, capped at 15. The board has 1 to 6 rows and columns, filled from an
alphabet of 1 to 4 random letters. Half of the time the word is read along a random walk
that never revisits a cell (so the answer is true); otherwise, or when no such walk of the
right length is found in a few tries, the word is random letters from the board's alphabet,
which usually has no walk but shares long prefixes with many. Words never contain a letter
missing from the board, which keeps the plain search's dead ends short enough for the
oracle cross-check.
"""

import random
import string

MAX_SIDE = 6
MIN_WORD = 1
MAX_WORD = 15
MAX_ALPHABET = 4
WALK_ATTEMPTS = 20
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _walk(rng: random.Random, board: list[list[str]], length: int) -> str | None:
    rows, cols = len(board), len(board[0])
    for _ in range(WALK_ATTEMPTS):
        r, c = rng.randrange(rows), rng.randrange(cols)
        path = [(r, c)]
        seen = {(r, c)}
        while len(path) < length:
            options = [
                (r + dr, c + dc)
                for dr, dc in STEPS
                if 0 <= r + dr < rows and 0 <= c + dc < cols and (r + dr, c + dc) not in seen
            ]
            if not options:
                break
            r, c = rng.choice(options)
            path.append((r, c))
            seen.add((r, c))
        if len(path) == length:
            return "".join(board[r][c] for r, c in path)
    return None


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_WORD), MAX_WORD)
    rows, cols = rng.randint(1, MAX_SIDE), rng.randint(1, MAX_SIDE)
    alphabet = rng.sample(string.ascii_lowercase, rng.randint(1, MAX_ALPHABET))
    board = [[rng.choice(alphabet) for _ in range(cols)] for _ in range(rows)]
    word = _walk(rng, board, length) if rng.random() < 0.5 else None
    if word is None:
        word = "".join(rng.choice(alphabet) for _ in range(length))
    return {"board": board, "word": word}


def validate(case_input: dict) -> None:
    board, word = case_input["board"], case_input["word"]
    assert 1 <= len(board) <= MAX_SIDE, "row count out of range"
    assert 1 <= len(board[0]) <= MAX_SIDE, "column count out of range"
    assert all(len(row) == len(board[0]) for row in board), "rows must have equal length"
    letters = set(string.ascii_lowercase)
    assert all(cell in letters for row in board for cell in row), "cells must be lowercase letters"
    assert MIN_WORD <= len(word) <= MAX_WORD, "word length out of range"
    assert set(word) <= letters, "word must be lowercase letters"
