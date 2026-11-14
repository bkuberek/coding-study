"""Leveling against tiering: how many entries each merge policy writes, and how many runs a lookup
may have to search.

4,096 distinct keys arrive; every 16 of them fill the memtable, which is flushed as a run. The size
ratio is T = 4. Leveling keeps one run per level, level i holding up to 16 * 4**(i + 1) entries:
each flush is merged into level 0, and a level pushed past its limit is merged into the next.
Tiering keeps up to 4 runs per level: a flush adds a run to level 0, and a level with 4 runs merges
them into one new run at the next level. A merge writes every entry of its inputs once.
"""

KEYS, FLUSH, T = 4096, 16, 4


def leveling() -> tuple[int, int]:
    levels: list[int] = []  # entries in the one run of each level, 0 when empty
    written = most_runs = 0
    for _ in range(KEYS // FLUSH):
        carry, i = FLUSH, 0
        while carry:
            if i == len(levels):
                levels.append(0)
            levels[i] += carry
            written += levels[i]
            carry = 0
            if levels[i] > FLUSH * T ** (i + 1):
                carry, levels[i] = levels[i], 0
                i += 1
        most_runs = max(most_runs, sum(1 for size in levels if size))
    return written, most_runs


def tiering() -> tuple[int, int]:
    levels: list[list[int]] = []  # the sizes of the runs at each level
    written = most_runs = 0
    for _ in range(KEYS // FLUSH):
        run, i = FLUSH, 0
        while run:
            if i == len(levels):
                levels.append([])
            levels[i].append(run)
            written += run
            run = 0
            if len(levels[i]) == T:
                run, levels[i] = sum(levels[i]), []
                i += 1
        most_runs = max(most_runs, sum(len(level) for level in levels))
    return written, most_runs


for name, policy in [("leveling", leveling), ("tiering", tiering)]:
    written, most_runs = policy()
    print(
        f"{name:<9} {written:>6,} entries written for {KEYS:,} keys:"
        f" {written / KEYS:.1f} writes per key, at most {most_runs} runs to search"
    )
