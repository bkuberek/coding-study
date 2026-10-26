"""Seeded inputs for valid-sudoku: a 9 x 9 board with `n` filled cells (at most 81).

The board starts from a solved grid: a fixed valid pattern with its digits relabeled, its
rows shuffled within each band and its bands shuffled, and likewise for columns and stacks.
Each of those changes keeps every row, column and box a permutation of 1..9. Then `n` random
cells keep their digits and the rest become ".".

In about half of the boards with at least one filled cell, the digit of the last filled cell
in row-major order is copied into another cell of its row, its column or its box, within the
same band of three rows, so the board breaks a rule (answer `false`). Every approach reads
the board in row-major order and stops at the conflict, so placing it in the last filled band
means a broken board costs about as much as a valid one with the same `n`.

The board size is fixed, but the work grows with `n`: every filled cell is checked against
its row, column and box, while empty cells are only skipped.
"""

import random

SIDE = 9
BOX = 3
CELLS = SIDE * SIDE
EMPTY = "."
DIGITS = "123456789"
CONFLICT_PROBABILITY = 0.5


def generate(rng: random.Random, n: int) -> dict:
    filled = min(max(n, 0), CELLS)
    grid = solved_grid(rng)
    kept = rng.sample(range(CELLS), filled)
    board = [[EMPTY] * SIDE for _ in range(SIDE)]
    for cell in kept:
        row, column = divmod(cell, SIDE)
        board[row][column] = grid[row][column]
    if kept and rng.random() < CONFLICT_PROBABILITY:
        _copy_into_same_unit(rng, board, divmod(max(kept), SIDE))
    return {"board": board}


def solved_grid(rng: random.Random) -> list[list[str]]:
    digits = list(DIGITS)
    rng.shuffle(digits)
    rows = _shuffled_lines(rng)
    columns = _shuffled_lines(rng)
    return [[digits[_pattern(row, column)] for column in columns] for row in rows]


def _pattern(row: int, column: int) -> int:
    """A valid solved grid: each row shifts the previous one by 3, each band by 1 more."""
    return (BOX * (row % BOX) + row // BOX + column) % SIDE


def _shuffled_lines(rng: random.Random) -> list[int]:
    return [
        band * BOX + offset
        for band in rng.sample(range(BOX), BOX)
        for offset in rng.sample(range(BOX), BOX)
    ]


def _copy_into_same_unit(rng: random.Random, board: list[list[str]], cell: tuple[int, int]) -> None:
    """Copy the digit at `cell` into another cell of one of its units, in the same band."""
    row, column = cell
    top, left = row - row % BOX, column - column % BOX
    unit = rng.choice(("row", "column", "box"))
    if unit == "row":
        others = [(row, other) for other in range(SIDE) if other != column]
    elif unit == "column":
        others = [(other, column) for other in range(top, top + BOX) if other != row]
    else:
        others = [
            (r, c)
            for r in range(top, top + BOX)
            for c in range(left, left + BOX)
            if (r, c) != (row, column)
        ]
    target_row, target_column = rng.choice(others)
    board[target_row][target_column] = board[row][column]


def validate(case_input: dict) -> None:
    board = case_input["board"]
    assert len(board) == SIDE, "the board must have 9 rows"
    for line in board:
        assert len(line) == SIDE, "every row must have 9 cells"
        assert all(cell == EMPTY or cell in DIGITS for cell in line), "cells are 1-9 or ."
