STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def longest_increasing_path(matrix: list[list[int]]) -> int:
    rows, columns = len(matrix), len(matrix[0])

    def neighbors(r: int, c: int):
        for dr, dc in STEPS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < columns:
                yield nr, nc

    # larger[r][c] counts the neighbors a path could still step up to from (r, c).
    larger = [[0] * columns for _ in range(rows)]
    for r in range(rows):
        for c in range(columns):
            larger[r][c] = sum(1 for nr, nc in neighbors(r, c) if matrix[nr][nc] > matrix[r][c])
    # Kahn's algorithm from the sinks: each round removes the cells whose larger neighbors are
    # all gone. A cell removed in round k starts a longest path of exactly k cells.
    layer = [(r, c) for r in range(rows) for c in range(columns) if larger[r][c] == 0]
    rounds = 0
    while layer:
        rounds += 1
        next_layer = []
        for r, c in layer:
            for nr, nc in neighbors(r, c):
                if matrix[nr][nc] < matrix[r][c]:
                    larger[nr][nc] -= 1
                    if larger[nr][nc] == 0:
                        next_layer.append((nr, nc))
        layer = next_layer
    return rounds
