from collections import deque


def swim_in_water(grid: list[list[int]]) -> int:
    n = len(grid)

    def reachable(time: int) -> bool:
        """Can the goal be reached when the water stands at `time`?"""
        if grid[0][0] > time:
            return False
        seen = [[False] * n for _ in range(n)]
        seen[0][0] = True
        queue = deque([(0, 0)])
        while queue:
            r, c = queue.popleft()
            if (r, c) == (n - 1, n - 1):
                return True
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < n and 0 <= nc < n and not seen[nr][nc] and grid[nr][nc] <= time:
                    seen[nr][nc] = True
                    queue.append((nr, nc))
        return False

    # The answer is at least both corner heights and at most the highest floor.
    low, high = max(grid[0][0], grid[n - 1][n - 1]), n * n - 1
    while low < high:
        middle = (low + high) // 2
        if reachable(middle):
            high = middle
        else:
            low = middle + 1
    return low
