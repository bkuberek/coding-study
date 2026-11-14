"""Accept exactly the valid n-queens boards, each once, in any order.

Each listed board is checked for shape and for attacks; duplicates are rejected; and the
count must equal the number of valid placements, computed here by a bitmask count. Distinct
valid boards that are as many as all valid boards are all of them, so the expected boards
(724 of them at n = 10) need not be stored.
"""


def _count_placements(n: int) -> int:
    full = (1 << n) - 1

    def count(columns: int, diagonals: int, anti_diagonals: int) -> int:
        if columns == full:
            return 1
        total = 0
        free = full & ~(columns | diagonals | anti_diagonals)
        while free:
            bit = free & -free
            free ^= bit
            total += count(columns | bit, (diagonals | bit) << 1 & full, (anti_diagonals | bit) >> 1)
        return total

    return count(0, 0, 0)


def _board_problem(board: object, n: int) -> str | None:
    if not isinstance(board, list) or len(board) != n:
        return f"a board must be a list of {n} rows, got {board!r}"[:200]
    columns: list[int] = []
    for row in board:
        if not isinstance(row, str) or len(row) != n or set(row) - {"Q", "."}:
            return f"row {row!r} must be {n} characters of 'Q' and '.'"[:200]
        if row.count("Q") != 1:
            return f"row {row!r} must hold exactly one queen"
        columns.append(row.index("Q"))
    for row_a in range(n):
        for row_b in range(row_a + 1, n):
            gap = columns[row_b] - columns[row_a]
            if gap == 0 or abs(gap) == row_b - row_a:
                return f"the queens in rows {row_a} and {row_b} attack each other in {board!r}"[:200]
    return None


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    n = case_input["n"]
    if not isinstance(output, list):
        return f"expected a list of boards, got {output!r}"[:200]
    seen: set[tuple[str, ...]] = set()
    for board in output:
        problem = _board_problem(board, n)
        if problem is not None:
            return problem
        key = tuple(board)
        if key in seen:
            return f"board {board!r} is listed more than once"[:200]
        seen.add(key)
    total = _count_placements(n)
    if len(seen) != total:
        return f"listed {len(seen)} boards, but a {n} by {n} board has {total} valid placements"
    return None
