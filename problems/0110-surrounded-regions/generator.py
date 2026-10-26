"""Seeded boards for surrounded-regions.

`n` is the number of cells; the board is roughly square (aspect ratio varies by seed, at most
200 by 200). Each cell is `'O'` with a probability between 0.3 and 0.6 per board, so boards
range from many small enclosed pockets to large regions that wind in from the edge.
"""

import math
import random

MAX_SIDE = 200


def generate(rng: random.Random, n: int) -> dict:
    cells = max(n, 1)
    if cells >= MAX_SIDE * MAX_SIDE:
        rows = cols = MAX_SIDE
    else:
        rows = min(MAX_SIDE, max(1, round(math.sqrt(cells) * rng.uniform(0.6, 1.6))))
        cols = min(MAX_SIDE, max(1, cells // rows))
    open_share = rng.uniform(0.3, 0.6)
    board = [["O" if rng.random() < open_share else "X" for _ in range(cols)] for _ in range(rows)]
    return {"board": board}


def validate(case_input: dict) -> None:
    board = case_input["board"]
    assert 1 <= len(board) <= MAX_SIDE, "row count out of range"
    assert all(len(row) == len(board[0]) for row in board), "rows differ in length"
    assert 1 <= len(board[0]) <= MAX_SIDE, "column count out of range"
    assert all(cell in ("X", "O") for row in board for cell in row), "cell is not X or O"
