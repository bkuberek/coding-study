from collections import deque


def pacific_atlantic(heights: list[list[int]]) -> list[list[int]]:
    rows, cols = len(heights), len(heights[0])

    def climb(coast: list[tuple[int, int]]) -> list[list[bool]]:
        """Cells whose water can reach this coast: search uphill from all coast cells at once."""
        reached = [[False] * cols for _ in range(rows)]
        for r, c in coast:
            reached[r][c] = True
        queue = deque(coast)
        while queue:
            r, c = queue.popleft()
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if (
                    0 <= nr < rows
                    and 0 <= nc < cols
                    and not reached[nr][nc]
                    and heights[nr][nc] >= heights[r][c]
                ):
                    reached[nr][nc] = True
                    queue.append((nr, nc))
        return reached

    pacific = climb(list({(0, c) for c in range(cols)} | {(r, 0) for r in range(rows)}))
    atlantic = climb(list({(rows - 1, c) for c in range(cols)} | {(r, cols - 1) for r in range(rows)}))
    return [[r, c] for r in range(rows) for c in range(cols) if pacific[r][c] and atlantic[r][c]]
