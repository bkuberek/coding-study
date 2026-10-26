import heapq


def minimum_obstacles(grid: list[list[int]]) -> int:
    rows, cols = len(grid), len(grid[0])
    removals = [[-1] * cols for _ in range(rows)]  # -1: not settled yet
    # Entries are (removals so far, row, column); entering a cell costs its own value.
    heap = [(0, 0, 0)]
    while heap:
        cost, r, c = heapq.heappop(heap)
        if removals[r][c] != -1:
            continue  # an outdated entry: the cell was settled earlier at a lower cost
        removals[r][c] = cost
        if (r, c) == (rows - 1, cols - 1):
            return cost
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols and removals[nr][nc] == -1:
                heapq.heappush(heap, (cost + grid[nr][nc], nr, nc))
    raise AssertionError("the goal is always reachable when every obstacle may be removed")
