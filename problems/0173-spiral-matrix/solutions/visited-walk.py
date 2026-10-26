DIRECTIONS = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # right, down, left, up: clockwise


def spiral_order(matrix: list[list[int]]) -> list[int]:
    rows, cols = len(matrix), len(matrix[0])
    visited = [[False] * cols for _ in range(rows)]
    order = []
    r = c = heading = 0
    for _ in range(rows * cols):
        order.append(matrix[r][c])
        visited[r][c] = True
        dr, dc = DIRECTIONS[heading]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < rows and 0 <= nc < cols) or visited[nr][nc]:
            heading = (heading + 1) % 4
            dr, dc = DIRECTIONS[heading]
            nr, nc = r + dr, c + dc
        r, c = nr, nc
    return order
