def pacific_atlantic(heights: list[list[int]]) -> list[list[int]]:
    rows, cols = len(heights), len(heights[0])

    def drains_to_both(start_r: int, start_c: int) -> bool:
        pacific = atlantic = False
        seen = {(start_r, start_c)}
        stack = [(start_r, start_c)]
        while stack:
            r, c = stack.pop()
            pacific = pacific or r == 0 or c == 0
            atlantic = atlantic or r == rows - 1 or c == cols - 1
            if pacific and atlantic:
                return True
            # Water runs to a neighbor that is not higher than the current cell.
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if (
                    0 <= nr < rows
                    and 0 <= nc < cols
                    and (nr, nc) not in seen
                    and heights[nr][nc] <= heights[r][c]
                ):
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return False

    return [[r, c] for r in range(rows) for c in range(cols) if drains_to_both(r, c)]
