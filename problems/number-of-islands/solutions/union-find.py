def num_islands(grid: list[list[str]]) -> int:
    rows, cols = len(grid), len(grid[0])
    parent = list(range(rows * cols))
    size = [1] * (rows * cols)

    def find(cell: int) -> int:
        root = cell
        while parent[root] != root:
            root = parent[root]
        while parent[cell] != root:
            parent[cell], cell = root, parent[cell]
        return root

    def union(a: int, b: int) -> bool:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return False
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a
        size[root_a] += size[root_b]
        return True

    islands = 0
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] != "1":
                continue
            islands += 1
            cell = row * cols + col
            # Looking right and down is enough: the left and upper neighbors already looked here.
            if col + 1 < cols and grid[row][col + 1] == "1" and union(cell, cell + 1):
                islands -= 1
            if row + 1 < rows and grid[row + 1][col] == "1" and union(cell, cell + cols):
                islands -= 1
    return islands
