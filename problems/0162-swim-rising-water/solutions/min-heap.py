import heapq


def swim_in_water(grid: list[list[int]]) -> int:
    n = len(grid)
    seen = [[False] * n for _ in range(n)]
    seen[0][0] = True
    # Entries are (highest floor on the route so far, row, column).
    heap = [(grid[0][0], 0, 0)]
    while heap:
        level, r, c = heapq.heappop(heap)
        if (r, c) == (n - 1, n - 1):
            return level
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < n and 0 <= nc < n and not seen[nr][nc]:
                seen[nr][nc] = True
                heapq.heappush(heap, (max(level, grid[nr][nc]), nr, nc))
    raise AssertionError("the goal is always reachable once the water covers every floor")
