"""A grid is a graph nobody stores: each open cell is a node, its edges computed on demand."""

FLOOR = [
    "..#.",
    ".##.",
    "....",
]
ROWS, COLUMNS = len(FLOOR), len(FLOOR[0])
STEPS = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right


def neighbors(row: int, column: int):
    for row_step, column_step in STEPS:
        r, c = row + row_step, column + column_step
        if 0 <= r < ROWS and 0 <= c < COLUMNS and FLOOR[r][c] == ".":
            yield (r, c)


for cell in [(0, 0), (0, 3), (2, 1), (2, 3)]:
    print(f"{cell} -> {list(neighbors(*cell))}")

open_cells = [(r, c) for r in range(ROWS) for c in range(COLUMNS) if FLOOR[r][c] == "."]
edge_ends = sum(len(list(neighbors(*cell))) for cell in open_cells)
print(f"{len(open_cells)} open cells, {edge_ends // 2} edges, none of them stored")
