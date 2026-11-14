def max_area_of_island(grid: list[list[int]]) -> int:
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

    def union(a: int, b: int) -> int:
        """Merge the groups of a and b; return the size of the merged group."""
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            if size[root_a] < size[root_b]:
                root_a, root_b = root_b, root_a
            parent[root_b] = root_a
            size[root_a] += size[root_b]
        return size[root_a]

    best = 0
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] != 1:
                continue
            cell = row * cols + col
            best = max(best, 1)
            if col + 1 < cols and grid[row][col + 1] == 1:
                best = max(best, union(cell, cell + 1))
            if row + 1 < rows and grid[row + 1][col] == 1:
                best = max(best, union(cell, cell + cols))
    return best
