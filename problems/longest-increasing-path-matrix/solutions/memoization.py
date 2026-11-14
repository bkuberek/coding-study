STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def longest_increasing_path(matrix: list[list[int]]) -> int:
    rows, columns = len(matrix), len(matrix[0])
    # longest[r][c] caches the longest increasing path that starts at (r, c); 0 is unknown.
    longest = [[0] * columns for _ in range(rows)]

    def explore(r: int, c: int) -> int:
        if longest[r][c] == 0:
            best = 1
            for dr, dc in STEPS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < columns and matrix[nr][nc] > matrix[r][c]:
                    best = max(best, 1 + explore(nr, nc))
            longest[r][c] = best
        return longest[r][c]

    return max(explore(r, c) for r in range(rows) for c in range(columns))
