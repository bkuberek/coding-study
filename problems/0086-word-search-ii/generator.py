"""Seeded inputs for word-search-ii.

`n` is the number of words. Small inputs (fewer than 100 words, the oracle sizes) get boards
of 1 to min(12, 2 + n / 2) rows and columns; larger inputs get 8 to 12. Half of the boards use
the letters `abcdef`, the other half all 26 letters. Half of the words are traced along random
self-avoiding walks on the board, so they are found; the others are random strings of board
letters, which are usually not. Words have 1 to 10 letters and are distinct.
"""

import random
import string

MAX_SIDE = 12
MAX_WORDS = 10**4
MAX_LENGTH = 10
LARGE_INPUT = 100
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_WORDS)
    smallest, largest = (8, MAX_SIDE) if count >= LARGE_INPUT else (1, min(MAX_SIDE, 2 + count // 2))
    rows, cols = rng.randint(smallest, largest), rng.randint(smallest, largest)
    alphabet = "abcdef" if rng.random() < 0.5 else string.ascii_lowercase
    board = [[rng.choice(alphabet) for _ in range(cols)] for _ in range(rows)]
    letters = sorted({letter for row in board for letter in row})
    words: dict[str, None] = {}
    attempts = 0
    while len(words) < count and attempts < 20 * count:
        attempts += 1
        if rng.random() < 0.5:
            word = _walk(rng, board, rng.randint(1, MAX_LENGTH))
        else:
            word = "".join(rng.choice(letters) for _ in range(rng.randint(1, MAX_LENGTH)))
        words[word] = None
    return {"board": board, "words": list(words)}


def validate(case_input: dict) -> None:
    board, words = case_input["board"], case_input["words"]
    assert 1 <= len(board) <= MAX_SIDE, "row count out of range"
    assert all(1 <= len(row) == len(board[0]) <= MAX_SIDE for row in board), "bad row length"
    assert all(len(cell) == 1 and "a" <= cell <= "z" for row in board for cell in row), "bad cell"
    assert 1 <= len(words) <= MAX_WORDS, "word count out of range"
    assert len(set(words)) == len(words), "words must be distinct"
    assert all(1 <= len(word) <= MAX_LENGTH for word in words), "word length out of range"
    assert all("a" <= letter <= "z" for word in words for letter in word), "only lowercase letters"


def _walk(rng: random.Random, board: list[list[str]], length: int) -> str:
    """Letters along a random self-avoiding walk of up to `length` cells."""
    rows, cols = len(board), len(board[0])
    row, col = rng.randrange(rows), rng.randrange(cols)
    used = {(row, col)}
    letters = [board[row][col]]
    while len(letters) < length:
        options = [
            (row + dr, col + dc)
            for dr, dc in STEPS
            if 0 <= row + dr < rows and 0 <= col + dc < cols and (row + dr, col + dc) not in used
        ]
        if not options:
            break
        row, col = rng.choice(options)
        used.add((row, col))
        letters.append(board[row][col])
    return "".join(letters)
