"""Seeded inputs for word-search.

The word length is n, capped at 15.

Words of 5 letters or more, which covers every size the ladder times, come from a trap that
neither approach can shortcut. A 6 by 6 board is filled with one letter; two cells inside
the border hold the word's first letter and two border cells its last letter, and the word
is the first letter, the filler repeated, then the last letter. Every count check passes and
both end letters are equally rare, so the search starts at both first-letter cells and
follows every walk through the filler. A walk of k steps changes the color
`(row + column) % 2` of its cell k times, and the last-letter cells sit on the color that a
walk of the word's length can never reach from the first start: its whole tree of walks is
searched and fails. Half of the time the second start, later in row-major order, takes the
other color and usually completes the word (the answer is true after one full tree);
otherwise it fails like the first. The work grows exponentially with the word at every seed,
within a factor of about 3 between seeds, without the early exits that a random board hits
at some sizes and not at others.

Shorter words use small random boards: 1 to 6 rows and columns over an alphabet of 1 to 4
random letters. Half of the time the word is read along a random walk that never revisits a
cell (so the answer is true); otherwise, or when no such walk of the right length is found in
a few tries, the word is random letters from the board's alphabet.
"""

import itertools
import random
import string

MAX_SIDE = 6
MIN_WORD = 1
MAX_WORD = 15
MAX_ALPHABET = 4
WALK_ATTEMPTS = 20
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))
TRAP_FROM = 5
END_LETTER_CELLS = 2
"""Cells per end letter: equal counts, so the pruned search never reverses the word."""

Cell = tuple[int, int]


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


def _random_board(rng: random.Random, length: int) -> dict:
    rows, cols = rng.randint(1, MAX_SIDE), rng.randint(1, MAX_SIDE)
    alphabet = rng.sample(string.ascii_lowercase, rng.randint(1, MAX_ALPHABET))
    board = [[rng.choice(alphabet) for _ in range(cols)] for _ in range(rows)]
    word = _walk(rng, board, length) if rng.random() < 0.5 else None
    if word is None:
        word = "".join(rng.choice(alphabet) for _ in range(length))
    return {"board": board, "word": word}


def _color(cell: Cell) -> int:
    return sum(cell) % 2


def _adjacent(cell: Cell, other: Cell) -> bool:
    return abs(cell[0] - other[0]) + abs(cell[1] - other[1]) == 1


def _starts(rng: random.Random, inner: list[Cell], blocked: int) -> list[Cell]:
    """Inner cells for the first letter, in row-major order: all of the blocked color, or,
    half of the time, all but the last, which takes the other color."""
    last_color = blocked if rng.random() < 0.5 else 1 - blocked
    return rng.choice(
        [
            [*earlier, last]
            for *earlier, last in itertools.combinations(inner, END_LETTER_CELLS)
            if all(_color(cell) == blocked for cell in earlier) and _color(last) == last_color
        ]
    )


def _trap(rng: random.Random, length: int) -> dict:
    filler, first, last = rng.sample(string.ascii_lowercase, 3)
    cells = [(r, c) for r in range(MAX_SIDE) for c in range(MAX_SIDE)]
    inner = [(r, c) for r, c in cells if 0 < r < MAX_SIDE - 1 and 0 < c < MAX_SIDE - 1]
    blocked = rng.randrange(2)
    starts = _starts(rng, inner, blocked)
    # A walk spelling the word takes length - 1 steps: it ends on this color only when it
    # starts on the other one.
    end_color = (blocked + length) % 2
    end_pool = [
        cell
        for cell in cells
        if cell not in inner
        and _color(cell) == end_color
        and not any(_adjacent(cell, start) for start in starts)
    ]
    board = [[filler] * MAX_SIDE for _ in range(MAX_SIDE)]
    for r, c in starts:
        board[r][c] = first
    for r, c in rng.sample(end_pool, END_LETTER_CELLS):
        board[r][c] = last
    return {"board": board, "word": first + filler * (length - 2) + last}


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_WORD), MAX_WORD)
    if length >= TRAP_FROM:
        return _trap(rng, length)
    return _random_board(rng, length)


def validate(case_input: dict) -> None:
    board, word = case_input["board"], case_input["word"]
    assert 1 <= len(board) <= MAX_SIDE, "row count out of range"
    assert 1 <= len(board[0]) <= MAX_SIDE, "column count out of range"
    assert all(len(row) == len(board[0]) for row in board), "rows must have equal length"
    letters = set(string.ascii_lowercase)
    assert all(cell in letters for row in board for cell in row), "cells must be lowercase letters"
    assert MIN_WORD <= len(word) <= MAX_WORD, "word length out of range"
    assert set(word) <= letters, "word must be lowercase letters"
