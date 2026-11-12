"""Two players take turns removing a coin from either end of a row and keep what they take.
The state is the stretch of the row still on the table: (i, j), the coins from i to j."""

from collections.abc import Callable

ROW = [8, 15, 3, 7]


def lead_table(row: list[int]) -> list[list[int]]:
    """lead[i][j]: how far ahead the player to move ends up on the coins i..j, against a rival who
    also plays as well as possible. Filled by stretch length, short to long; only i <= j is used."""
    n = len(row)
    lead = [[0] * n for _ in range(n)]
    for i in range(n):
        lead[i][i] = row[i]  # one coin left: take it
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            # after taking a coin, the rival is the one to move on what is left
            lead[i][j] = max(row[i] - lead[i + 1][j], row[j] - lead[i][j - 1])
    return lead


lead = lead_table(ROW)
print("lead[i][j]" + "".join(f"{f'j={j}':>6}" for j in range(len(ROW))))
for i, cells in enumerate(lead):
    shown = ["" if j < i else str(cell) for j, cell in enumerate(cells)]
    print(f"{f'i={i}':10}" + "".join(f"{cell:>6}" for cell in shown))
total = sum(ROW)
print(f"first player: {(total + lead[0][-1]) // 2}, second: {(total - lead[0][-1]) // 2}")


def play(row: list[int], takes_left: Callable[[int, int], bool]) -> list[int]:
    """The two players' totals when both take the left coin exactly when takes_left(i, j)."""
    totals, i, j, player = [0, 0], 0, len(row) - 1, 0
    while i <= j:
        if takes_left(i, j):
            totals[player] += row[i]
            i += 1
        else:
            totals[player] += row[j]
            j -= 1
        player = 1 - player
    return totals


def table_says_left(i: int, j: int) -> bool:
    return i == j or ROW[i] - lead[i + 1][j] >= ROW[j] - lead[i][j - 1]


print("both follow the table:", play(ROW, table_says_left))
print("both take the larger end:", play(ROW, lambda i, j: ROW[i] >= ROW[j]))
