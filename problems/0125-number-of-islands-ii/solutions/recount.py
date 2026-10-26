STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def num_islands2(m: int, n: int, positions: list[list[int]]) -> list[int]:
    land = [[False] * n for _ in range(m)]
    cells: list[tuple[int, int]] = []  # every land cell, each once

    def count_islands() -> int:
        seen: set[tuple[int, int]] = set()
        islands = 0
        for start in cells:
            if start in seen:
                continue
            islands += 1
            seen.add(start)
            stack = [start]
            while stack:
                r, c = stack.pop()
                for dr, dc in STEPS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < m and 0 <= nc < n and land[nr][nc] and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
        return islands

    counts: list[int] = []
    for r, c in positions:
        if not land[r][c]:
            land[r][c] = True
            cells.append((r, c))
        counts.append(count_islands())
    return counts
