"""A take-away game, solved with a table: a move takes 1, 3 or 4 stones from one pile, and the
player who takes the last stone wins."""

MOVES = (1, 3, 4)


def winning_table(stones: int) -> list[bool]:
    """win[n]: the player about to move, facing n stones, can force a win."""
    win = [False] * (stones + 1)  # win[0] stays False: no stones left, so no move to make
    for n in range(1, stones + 1):  # increasing n: every cell read below is already filled
        win[n] = any(move <= n and not win[n - move] for move in MOVES)
    return win


def row(label: str, cells: list[str]) -> str:
    return f"{label:10}" + "".join(f"{cell:>3}" for cell in cells)


def wins(win: list[bool]) -> list[str]:
    return ["W" if cell else "L" for cell in win]


table = winning_table(14)
print(row("n", [str(n) for n in range(15)]))
print(row("win[n]", wins(table)))

n, game = 12, []
while n > 0:  # replay: the mover always takes a move that leaves a losing position, if one exists
    move = next((m for m in MOVES if m <= n and not table[n - m]), 1)
    game.append(f"{n} -{move}")
    n -= move
print("a game from 12:", ", ".join(game), "-> 0")


def unguarded_table(stones: int) -> list[bool]:
    """The same loop without `move <= n`: win[n - move] with a negative index reads the far end."""
    win = [False] * (stones + 1)
    for n in range(1, stones + 1):
        win[n] = any(not win[n - move] for move in MOVES)
    return win


print(row("unguarded", wins(unguarded_table(14))))


def wins_with_four_cells(stones: int) -> bool:
    """The same answer for one n, keeping only the last four cells in a ring of four slots."""
    ring = [False] * 4  # ring[k % 4] holds win[k] for the four most recent k
    for n in range(1, stones + 1):
        result = any(move <= n and not ring[(n - move) % 4] for move in MOVES)
        ring[n % 4] = result  # overwrites win[n - 4], which was read just above
    return ring[stones % 4]


big = winning_table(10_000)
losing = [n for n in range(60) if not big[n]]
print("losing positions below 60:", losing)
pattern_holds = all(big[n] == (n % 7 not in (0, 2)) for n in range(10_001))
print("n loses exactly when n % 7 is 0 or 2, for every n up to 10,000:", pattern_holds)
ring_agrees = all(wins_with_four_cells(n) == big[n] for n in range(1_001))
print("ring of four slots agrees up to 1,000:", ring_agrees)
