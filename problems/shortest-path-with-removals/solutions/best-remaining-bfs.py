from collections import deque


def shortest_path(grid: list[list[int]], k: int) -> int:
    rows, cols = len(grid), len(grid[0])
    shortest = rows + cols - 2
    # Enough removals for the straight Manhattan route: nothing can beat it.
    if k >= rows + cols - 3:
        return shortest
    # best[r][c] is the most removals left with which (r, c) was reached so far.
    best = [[-1] * cols for _ in range(rows)]
    best[0][0] = k
    queue = deque([(0, 0, k)])
    moves = 0
    while queue:
        for _ in range(len(queue)):
            r, c, left = queue.popleft()
            if (r, c) == (rows - 1, cols - 1):
                return moves
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                remaining = left - grid[nr][nc]
                # A visit that arrives later with no more removals left can never do better.
                if remaining > best[nr][nc]:
                    best[nr][nc] = remaining
                    queue.append((nr, nc, remaining))
        moves += 1
    return -1
