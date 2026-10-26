from collections import deque


def shortest_path(grid: list[list[int]], k: int) -> int:
    rows, cols = len(grid), len(grid[0])
    # A Manhattan route enters at most rows + cols - 3 cells besides the corners, so more
    # removals than that never help.
    budget = min(k, max(0, rows + cols - 3))
    seen = [[[False] * (budget + 1) for _ in range(cols)] for _ in range(rows)]
    seen[0][0][0] = True
    queue = deque([(0, 0, 0)])
    moves = 0
    while queue:
        for _ in range(len(queue)):
            r, c, used = queue.popleft()
            if (r, c) == (rows - 1, cols - 1):
                return moves
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                after = used + grid[nr][nc]
                if after <= budget and not seen[nr][nc][after]:
                    seen[nr][nc][after] = True
                    queue.append((nr, nc, after))
        moves += 1
    return -1
